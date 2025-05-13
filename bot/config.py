import os
import json

# Отримуємо токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не встановлено у змінних середовища.")

# Отримуємо Firebase credentials як JSON-рядок
firebase_json = os.getenv("FIREBASE_KEY_PATH")
if not firebase_json:
    raise ValueError("❌ FIREBASE_KEY_PATH не встановлено у змінних середовища.")

try:
    FIREBASE_KEY_PATH = json.loads(firebase_json)
except json.JSONDecodeError as e:
    raise ValueError(f"❌ Не вдалося розпарсити FIREBASE_KEY_PATH як JSON: {e}")
