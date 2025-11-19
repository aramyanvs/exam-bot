# config.py
import os
from pathlib import Path


# --- Простая подгрузка .env (локально) ---

def _load_dotenv():
    """
    Очень простой загрузчик .env:
    - читает файл .env в текущей папке (если есть)
    - строки формата KEY=VALUE записывает в os.environ,
      если там ещё не задано.
    """
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


# Сначала пробуем подгрузить локальный .env (на Railway он не нужен)
_load_dotenv()

# --- Настройки бота ---

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN (ни в переменных окружения, ни в .env)")

_admin_chat_raw = os.getenv("ADMIN_CHAT_ID", "").strip()
if not _admin_chat_raw:
    raise RuntimeError("Не задан ADMIN_CHAT_ID в переменных окружения (.env или Railway)")

try:
    ADMIN_CHAT_ID = int(_admin_chat_raw)
except ValueError:
    raise RuntimeError("ADMIN_CHAT_ID должен быть целым числом (chat_id Telegram)")

# Путь к базе (по умолчанию — файл в той же папке, что и скрипты)
DB_PATH = os.getenv("DB_PATH") or str((Path(__file__).parent / "exam_bot.db").resolve())
