import os

# Bot token
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Gemini API keys (TEKIN)
GEMINI_API_KEYS = [
    os.getenv("GEMINI_API_KEY", ""),
]

# Anthropic Claude API key (PULLIK)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Admin panel URL
ADMIN_PANEL_URL = os.getenv("ADMIN_PANEL_URL", "https://web-production-d7fca.up.railway.app")

# Database path
DB_PATH = os.getenv("DB_PATH", "expenses.db")

# Gemini models (TEKIN - 10+ model)
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

# Claude model (ENG ARZON - Haiku)
CLAUDE_MODEL = "claude-3-haiku-20240307"  # $0.25 per 1M input tokens