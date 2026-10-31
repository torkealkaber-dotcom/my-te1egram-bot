import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

# Factory Bot
FACTORY_BOT_TOKEN = os.getenv("FACTORY_BOT_TOKEN", "")

# Developers
OWNER_ID = int(os.getenv("OWNER_ID", "8909680386"))
PARTNER_ID = int(os.getenv("PARTNER_ID", "8404122925"))
DEVELOPERS = {OWNER_ID, PARTNER_ID}

OWNER_GROUP_ID = int(os.getenv("OWNER_GROUP_ID", "0"))

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "")

# Factory Settings
MAX_USER_BOTS = int(os.getenv("MAX_USER_BOTS", "1"))
MAX_OWNER_BOTS = int(os.getenv("MAX_OWNER_BOTS", "6"))

# Music Settings
FACTORY_DEV_USERNAME = os.getenv(
    "FACTORY_DEV_USERNAME", "@YourUsername"
)

SOURCE_CHANNEL = os.getenv(
    "SOURCE_CHANNEL", "https://t.me/YourChannel"
)

# Keyboard Settings
DEFAULT_BUTTON_STYLE = "primary"

# Message Formatting
PARSE_MODE = "HTML"


def is_developer(user_id: int) -> bool:
    return user_id in DEVELOPERS


def validate_config():
    required = {
        "API_ID": API_ID,
        "API_HASH": API_HASH,
        "FACTORY_BOT_TOKEN": FACTORY_BOT_TOKEN,
        "SECRET_KEY": SECRET_KEY,
    }

    missing = [
        name for name, value in required.items()
        if not value
    ]

    if missing:
        raise ValueError(
            "Missing configuration: " + ", ".join(missing)
        )
