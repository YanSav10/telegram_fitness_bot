import os
from pathlib import Path
from dotenv import load_dotenv
import json

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")

FIREBASE_KEY_PATH = BASE_DIR / "firebase_key.json"

firebase_json = os.getenv("FIREBASE_CREDENTIALS_JSON")

if firebase_json:
    with open(FIREBASE_KEY_PATH, "w") as f:
        json.dump(json.loads(firebase_json), f)
