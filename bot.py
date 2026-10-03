import logging
import os
from datetime import datetime
import pycountry
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config

# Set up logging
logging.basicConfig(level=logging.INFO)

# Duplicate OTP Tracking Cache
processed_sms_ids = set()

# In-Memory Database (Initial Stock Data)
stock_db = {
    "Cambodia": {"code": "KH", "numbers": ["+85561615823", "+85577740100", "+85589830229", "+85578424599", "+85517446705"]},
    "Peru": {"code": "PE", "numbers": ["+51910681051", "+51910681052"]},
    "Sudan": {"code": "SD", "numbers": ["+249912345678"]},
    "Sri Lanka": {"code": "LK", "numbers": ["+94771234567"]}
}

# Helper Functions
def get_country_flag(country_code: str) -> str:
    """Generates flag emoji dynamically from country code"""
    try:
        country_code = country_code.upper()
        return chr(ord(country_code[0]) + 127397) + chr(ord(country_code[1]) + 127397)
    except Exception:
        return "🌐"

def mask_phone_number(phone_number: str, mask_symbol: str = "🧸") -> str:
    """Masks phone number (e.g. +5191🧸1051)"""
    phone = str(phone_number).strip()
    if len(phone) <= 8:
        return phone
    return f"{phone[:5]}{mask_symbol}{phone[-4:]}"

def is_duplicate_sms(sms_id: str) -> bool:
    """Filters duplicate OTP requests"""
    if sms_id in processed_sms_ids:
        return True
    processed_sms_ids.add(sms_id)
    if len(processed_sms_ids) > 10000:
        processed_sms_ids.clear()
    return False

def detect_service_and_logo(sms_text: str):
    """Detects service name and emoji logo from SMS body"""
    text_lower = sms_text.lower()
    services = {
        "whatsapp": ("🟢 WhatsApp", "📱"),
        "telegram": ("✈️ Telegram", "🔹"),
        "facebook": ("🔵 Facebook", "👤"),
        "imo": ("🟣 IMO", "📞"),
        "viber": ("💜 Viber", "📱"),
        "tiktok": ("🎵 TikTok", "🖤"),
        "google": ("🔴 Google", "📧"),
    }
    for key, (service_name, logo) in services.items():
        if key in text_lower:
            return service_name, logo
    return "🌐 Service", "📩"

# User Keyboards
def main_keyboard():
    keyboard = [
        ["📥 Get Number", "⬇️ Get File"],
        ["🔍 Check OTP", "⚡️ Live Traffic"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# User Command & Menu Handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the SMS & OTP Management Bot!",
        reply_markup=main_keyboard()
    )

async def handle_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📥 Get Number":
        country_name = "Cambodia"
        country_info = stock_db.get(country_name, {"code": "KH", "numbers": []})
        numbers = country_info["numbers"]
        flag = get_country_flag(country_info["code"])
        current_time = datetime.now().strftime("%H:%M:%S")

        msg_text = (
            f"🟢 {flag} **{country_name.upper()} {len(numbers)} Numbers:**\n"
            f"_Waiting for OTP... (Session: 30 Min)_\n"
            f"Last sync: `{current_time}`"
        )

        keyboard = []
        for num in numbers:
            keyboard.append([InlineKeyboardButton(f"🟢 📋 {num}", switch_inline_query=num)])

        all_numbers_str = "\n".join(numbers)
        keyboard.append([InlineKeyboardButton("📋 COPY ALL NUMBER", switch_inline_query=all_numbers_str)])
        keyboard.append([
            InlineKeyboardButton("🔄 Change Number", callback_data=f"change_num_{country_name}"),
            InlineKeyboardButton("🌐 Change Country", callback_data="show_countries")
        ])
        keyboard.append([InlineKeyboardButton("↗️ OTP Group", url=config.CHANNEL_URL)])

        await update.message.reply_text(
            text=msg_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif text == "⬇️ Get File":
        await update.message.reply_text("📄 Generating bulk numbers file for download...")

    elif text == "🔍 Check OTP":
        await update.message.reply_text("🔍 Please enter your phone number to check OTP status:")

    elif text == "⚡️ Live Traffic":
        traffic_msg = (
            "⚡️ **Live Traffic — 30 Min**\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
            "🥇 🇸🇩 **Sudan** 🟢 ▓▓▓▓▓░░░░░\n51.1% ✅\n"
            "🥈 🇨🇩 **DR Congo** 🟢 ▓▓░░░░░░░░\n21.8% ✅\n"
            "🥉 🇵🇪 **Peru** 🟢 ▓▓░░░░░░░░\n19.7% ✅\n"
            "4. 🇱🇰 **Sri Lanka** 🟢 ░░░░░░░░░░\n5.3% 🟢\n"
            "5. 🇲🇿 **Mozambique** 🟢 ░░░░░░░░░░\n2.1% 🟡\n\n"
            "📊 **188 SMS • Live UTC**"
        )
        refresh_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="refresh_traffic")]])
        await update.message.reply_text(text=traffic_msg, reply_markup=refresh_kb, parse_mode='Markdown')

# Admin Commands & Handlers
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        return

    admin_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Stock Status", callback_data="admin_stock"), InlineKeyboardButton("🗑 Clear Stock", callback_data="admin_clear_stock_menu")],
        [InlineKeyboardButton("🔢 Set User Limit", callback_data="admin_limit"), InlineKeyboardButton("📄 Set File Limit", callback_data="admin_file_limit")],
        [InlineKeyboardButton("📢 Broadcast Msg", callback_data="admin_broadcast"), InlineKeyboardButton("📥 Export Backup", callback_data="admin_export")]
    ])
    await update.message.reply_text("⚙️ **Admin Control Panel**\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯", reply_markup=admin_kb, parse_mode='Markdown')

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "admin_clear_stock_menu":
        keyboard = []
        for country, info in stock_db.items():
            flag = get_country_flag(info["code"])
            btn_text = f"🗑 {flag} {country} ({len(info['numbers'])})"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"del_cat_{country}")])
        
        keyboard.append([InlineKeyboardButton("♻️ Clear Expired / Used Only", callback_data="del_used_only")])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="admin_back")])

        await query.edit_message_text(
            text="🗑 **Select Country Category to Clear Stock:**\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif data.startswith("del_cat_"):
        country_to_del = data.replace("del_cat_", "")
        if country_to_del in stock_db:
            stock_db[country_to_del]["numbers"] = []
            await query.edit_message_text(f"✅ Successfully cleared stock for **{country_to_del}**!", parse_mode='Markdown')

# Group OTP Forwarding Function
async def send_otp_to_group(bot, sms_id: str, country_code: str, phone_number: str, otp_code: str, sms_text: str):
    if is_duplicate_sms(sms_id):
        return

    flag = get_country_flag(country_code)
    masked_num = mask_phone_number(phone_number, mask_symbol="🧸")
    
    message_text = (
        f"**TJN x SMS PANEL...**  `NUMBER BOT`\n"
        f"{flag} **{country_code.upper()}** | 🟢 **{masked_num}**"
    )

    keyboard = [
        [InlineKeyboardButton(f"🔒 📋 {otp_code}", switch_inline_query=otp_code)],
        [
            InlineKeyboardButton("📱 Number ↗️", url=f"https://t.me/{config.BOT_USERNAME}?start=get_num"),
            InlineKeyboardButton("📢 Channel ↗️", url=config.CHANNEL_URL)
        ]
    ]

    await bot.send_message(
        chat_id=config.OTP_GROUP_ID,
        text=message_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def main():
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_menu))
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    print("🚀 Bot running successfully on Railway...")
    app.run_polling()

if __name__ == '__main__':
    main()