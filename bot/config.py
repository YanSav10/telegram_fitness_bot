import os
from pathlib import Path
from dotenv import load_dotenv

# Завантажуємо змінні з .env
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

# Токен бота (отримуємо з .env або задаємо вручну)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Шлях до Firebase JSON-ключа (відносно кореневої папки fitness_bot/)
FIREBASE_KEY_PATH = str(BASE_DIR / "firebase_key.json")
