import os
import json
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Отримуємо JSON-ключ як рядок зі змінної середовища
firebase_json = os.getenv("FIREBASE_KEY_PATH")

if firebase_json:
    FIREBASE_CREDENTIALS = json.loads(firebase_json)
else:
    raise ValueError("❌ Firebase credentials not found in FIREBASE_KEY_PATH")
