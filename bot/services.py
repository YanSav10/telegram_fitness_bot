import firebase_admin
from firebase_admin import credentials, firestore
from .config import FIREBASE_KEY_PATH
from datetime import datetime
from google.cloud.firestore_v1 import SERVER_TIMESTAMP, Query

# Ініціалізація Firebase з додатковою обробкою помилок
try:
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase успішно ініціалізовано")
except Exception as e:
    db = None
    print(f"❌ Firebase не вдалося ініціалізувати: {e}")

# Збереження даних користувача з додатковою перевіркою
def save_user(user_id, username, goal, height, weight, age):
    if db is None:
        print(f"⚠ Firebase недоступний. Дані не збережено для користувача {user_id}.")
        return

    user_data = {
        "user_id": user_id,
        "username": username,
        "goal": goal,
        "height": height,
        "weight": weight,
        "age": age,
        "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        db.collection("users").document(str(user_id)).set(user_data)
        print(f"✅ Дані для користувача {username} ({user_id}) успішно збережені в Firestore")
    except Exception as e:
        print(f"❌ Помилка при збереженні даних у Firestore: {e}")

# Отримання даних користувача
def get_user(user_id):
    if db is None:
        print(f"⚠ Firebase недоступний. Неможливо отримати дані для користувача {user_id}.")
        return None

    try:
        doc = db.collection("users").document(str(user_id)).get()
        if doc.exists:
            print(f"✅ Дані для користувача {user_id} отримано")
            return doc.to_dict()
        else:
            print(f"⚠ Дані для користувача {user_id} не знайдено.")
            return None
    except Exception as e:
        print(f"❌ Помилка при отриманні даних користувача: {e}")
        return None

# Збереження прогресу тренувань користувача
def save_workout_progress(user_id, workout, duration):
    if db is None:
        print(f"⚠ Firebase недоступний. Прогрес тренування не збережено для користувача {user_id}.")
        return

    progress_data = {
        "workout": workout,
        "duration": duration,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": SERVER_TIMESTAMP
    }

    try:
        db.collection("users").document(str(user_id)).collection("workouts").add(progress_data)
        print(f"✅ Прогрес тренування для користувача {user_id} успішно збережений у Firestore")
    except Exception as e:
        print(f"❌ Помилка при збереженні прогресу тренування: {e}")

# Отримання історії тренувань користувача
def get_progress(user_id):
    if db is None:
        print(f"⚠ Firebase недоступний. Неможливо отримати прогрес для користувача {user_id}.")
        return []

    try:
        progress_ref = db.collection("users").document(str(user_id)).collection("workouts")
        progress_docs = progress_ref.order_by("timestamp", direction=Query.DESCENDING).stream()
        progress_list = [doc.to_dict() for doc in progress_docs]
        print(f"✅ Історія тренувань для користувача {user_id} отримана (записів: {len(progress_list)})")
        return progress_list
    except Exception as e:
        print(f"❌ Помилка при отриманні історії тренувань: {e}")
        return []

def check_achievements(user_id):
    achievements = []
    history = get_progress(user_id)
    count = len(history)
    if count == 5:
        achievements.append("Ви завершили 5 тренувань! 🔥")
    if count == 10:
        achievements.append("10 тренувань! Ви на шляху до успіху! 💪")
    if count == 20:
        achievements.append("20 тренувань! Ви легенда! 🏆")
    return achievements

def get_all_users():
    if db is None:
        print("⚠ Firebase недоступний. Неможливо отримати користувачів.")
        return []

    try:
        users = db.collection("users").stream()
        return [u.to_dict() for u in users]
    except Exception as e:
        print(f"❌ Помилка при отриманні користувачів: {e}")
        return []
