import os

# Bot token
BOT_TOKEN = os.getenv("BOT_TOKEN", "8772423332:AAFYXp4-yUDI79MS_q8jqOfjL6teG4BKXC4")

# Gemini API keys (10+ model uchun)
GEMINI_API_KEYS = [
    os.getenv("GEMINI_API_KEY", "AIzaSyC23doz7D0p8GKnP-FTAWqpnLCuI0RxaV0"),
]

# Admin panel URL
ADMIN_PANEL_URL = os.getenv("ADMIN_PANEL_URL", "https://web-production-d7fca.up.railway.app")

# Database path
DB_PATH = os.getenv("DB_PATH", "expenses.db")

# Gemini models (fallback list)
GEMINI_MODELS = [
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash-002",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-flash",
    "gemini-pro",
    "gemini-1.5-pro-latest",
    "gemini-1.5-pro-002",
    "gemini-1.5-pro-001"
]