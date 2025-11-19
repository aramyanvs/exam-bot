import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN в переменных окружения")

if not ADMIN_CHAT_ID:
    raise RuntimeError("Не задан ADMIN_CHAT_ID в переменных окружения")

try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
except ValueError:
    raise RuntimeError("ADMIN_CHAT_ID должен быть числом (chat id администратора)")
