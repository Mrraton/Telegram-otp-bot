import os

# Telegram Bot Credentials
BOT_TOKEN = os.getenv("BOT_TOKEN", "8824026653:AAHHcjXc3lI-mlR361MRFxsbkKwq0cvnJfI")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5872360608"))
OTP_GROUP_ID = int(os.getenv("OTP_GROUP_ID", "-1003355962140"))

# Navigation Links & Identity
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/your_channel")
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot_username")

# Operational Limits
DEFAULT_USER_LIMIT = 3
DEFAULT_FILE_LIMIT = 100