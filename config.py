import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8772423332:AAFYXp4-yUDI79MS_q8jqOfjL6teG4BKXC4")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyC23doz7D0p8GKnP-FTAWqpnLCuI0RxaV0")
ADMIN_PANEL_URL = os.getenv("ADMIN_PANEL_URL", "http://localhost:5000")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY topilmadi!")
