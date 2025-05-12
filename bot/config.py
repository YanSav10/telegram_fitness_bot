import os
import json
from pathlib import Path
from dotenv import load_dotenv

# ====== Завантаження локальних змінних (тільки для локального запуску) ======
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# ====== Токен бота ======
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")

# ====== Firebase ключ (JSON з Render або шлях до файлу локально) ======
firebase_json = os.getenv("FIREBASE_CREDENTIALS_JSON")

if firebase_json:
    FIREBASE_CREDENTIALS = json.loads(firebase_json)  # Render
else:
    FIREBASE_KEY_PATH = BASE_DIR / "firebase_key.json"
    with open(FIREBASE_KEY_PATH, "r") as f:
        FIREBASE_CREDENTIALS = json.load(f)  # Локально
