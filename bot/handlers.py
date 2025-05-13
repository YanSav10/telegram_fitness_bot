import re
import asyncio
from datetime import datetime, timezone, timedelta
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.services import (
    save_user, save_workout_progress,
    get_user, check_achievements,
    get_all_users, get_progress
)
from bot.buttons import goal_buttons, control_buttons, resume_buttons
from bot.workouts import workout_plans
from bot.video_links import video_links

router = Router()

class Form(StatesGroup):
    goal = State()
    height = State()
    weight = State()
    age = State()
    workout_choice = State()
    workout = State()

paused_workouts = {}

def get_explanation_button(exercise_name: str):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔍 Показати пояснення",
            callback_data=f"explain:{exercise_name}"
        )
    ]])

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "*Привіт, я твій фітнес-бот!*\n\n"
        "Я допоможу тобі слідкувати за тренуваннями і досягненнями.\n"
        "Вибери мету нижче ⬇",
        reply_markup=goal_buttons,
        parse_mode="Markdown"
    )
    await state.set_state(Form.goal)

@router.message(Form.goal, F.text.in_(["🔥 Схуднення", "💪 Набір маси", "🏃 Витривалість", "⚡ Сила"]))
async def process_goal(message: types.Message, state: FSMContext):
    await state.update_data(goal=message.text)
    await message.answer("Тепер введіть *зріст* (у см):", parse_mode="Markdown")
    await state.set_state(Form.height)

@router.message(Form.goal)
async def invalid_goal(message: types.Message):
    await message.answer("⚠ Натисни кнопку знизу для вибору мети!", parse_mode="Markdown")

@router.message(Form.height, F.text.isdigit())
async def process_height(message: types.Message, state: FSMContext):
    height = int(message.text)
    if 100 <= height <= 250:
        await state.update_data(height=height)
        await message.answer("Тепер введіть *вагу* (у кг):", parse_mode="Markdown")
        await state.set_state(Form.weight)
    else:
        await message.answer("❌ Реальний зріст: 100–250 см", parse_mode="Markdown")

@router.message(Form.height)
async def invalid_height(message: types.Message):
    await message.answer("🚫 Введи *число* (наприклад: 175).", parse_mode="Markdown")

@router.message(Form.weight, F.text.isdigit())
async def process_weight(message: types.Message, state: FSMContext):
    weight = int(message.text)
    if 30 <= weight <= 200:
        await state.update_data(weight=weight)
        await message.answer("Тепер введіть *вік*:", parse_mode="Markdown")
        await state.set_state(Form.age)
    else:
        await message.answer("❌ Реальна вага: 30–200 кг", parse_mode="Markdown")

@router.message(Form.weight)
async def invalid_weight(message: types.Message):
    await message.answer("🚫 Введи *число* (наприклад: 70).", parse_mode="Markdown")

@router.message(Form.age, F.text.isdigit())
async def process_age(message: types.Message, state: FSMContext):
    age = int(message.text)
    if 10 <= age <= 100:
        await state.update_data(age=age)
        data = await state.get_data()
        user = message.from_user
        username = user.username or f"{user.first_name or ''} {user.last_name or ''}".strip()
        if not username:
            username = f"user_{user.id}"
        save_user(user.id, username, data["goal"], data["height"], data["weight"], age)
        await message.answer(
            f"✅ Дані збережено!\n\n"
            f"👤 *Користувач:* @{username}\n"
            f"🎯 *Мета:* {data['goal']}\n"
            f"📏 *Зріст:* {data['height']} см\n"
            f"⚖ *Вага:* {data['weight']} кг\n"
            f"🎂 *Вік:* {age} років\n\n"
            f"🔹 Введи /workout для старту тренування",
            parse_mode="Markdown"
        )
        await state.clear()
    else:
        await message.answer("❌ Вік має бути від 10 до 100 років", parse_mode="Markdown")

@router.message(Form.age)
async def invalid_age(message: types.Message):
    await message.answer("🚫 Введи *число* (наприклад: 25).", parse_mode="Markdown")

@router.message(Command("workout"))
async def start_workout(message: types.Message, state: FSMContext):
    user_data = get_user(message.from_user.id)
    if not user_data:
        await message.answer("🚫 Ви ще не заповнили анкету. Введіть /start.")
        return

    goal = user_data["goal"]
    workouts = workout_plans[goal]["daily_workouts"]
    buttons = [[types.KeyboardButton(text=w.split("\n")[0].replace('🏋 ', ''))] for w in workouts]
    workout_choice_buttons = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    await message.answer("🔹 Оберіть тренування:", reply_markup=workout_choice_buttons)
    await state.set_state(Form.workout_choice)

@router.message(Form.workout_choice)
async def process_workout_choice(message: types.Message, state: FSMContext):
    user_data = get_user(message.from_user.id)
    goal = user_data["goal"]
    workouts = workout_plans[goal]["daily_workouts"]
    selected_workout = next((w for w in workouts if message.text in w), None)

    if selected_workout:
        await state.update_data(workout=selected_workout, user_id=message.from_user.id)
        await message.answer(
            f"{selected_workout}\n🔴 Старт для початку",
            reply_markup=control_buttons
        )
        await state.set_state(Form.workout)
    else:
        await message.answer("❌ Такого тренування немає. Спробуйте ще раз.")

@router.message(Form.workout, F.text == "🔴 Старт")
async def start_timer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    workout = data["workout"]
    user_id = data["user_id"]
    exercises = re.findall(r"✅ (\d+) сек ([^\n]+) \(x(\d+)\)", workout)
    total_duration = 0

    paused_workouts[user_id] = {"paused": False, "stopped": False}

    for sec, exercise, repeat in exercises:
        sec, repeat = int(sec), int(repeat)
        for r in range(repeat):
            caption = f"🔹 <b>{exercise}</b> — підхід {r + 1}/{repeat}"
            await message.answer(
                caption,
                parse_mode="HTML",
                reply_markup=get_explanation_button(exercise)
            )

            # 2. Вивід окремого повідомлення для таймера
            timer_msg = await message.answer(
                f"⏱️ Залишилось: {sec} сек",
                parse_mode="HTML"
            )

            for i in range(sec, 0, -1):
                await asyncio.sleep(1)

                if paused_workouts[user_id]["stopped"]:
                    await message.answer("⛔ Тренування зупинено.", reply_markup=types.ReplyKeyboardRemove())
                    await state.clear()
                    paused_workouts.pop(user_id, None)
                    return

                while paused_workouts[user_id]["paused"]:
                    await asyncio.sleep(1)

                try:
                    await timer_msg.edit_text(
                        f"⏱️ Залишилось: {i} сек",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"⚠ Не вдалося оновити таймер: {e}")

            total_duration += sec

            if r < repeat - 1:
                rest_msg = await message.answer("⏸️ Відпочинок 10 сек")
                for i in range(10, 0, -1):
                    await asyncio.sleep(1)

                    if paused_workouts[user_id]["stopped"]:
                        await message.answer("⛔ Тренування зупинено.", reply_markup=types.ReplyKeyboardRemove())
                        await state.clear()
                        paused_workouts.pop(user_id, None)
                        return

                    while paused_workouts[user_id]["paused"]:
                        await asyncio.sleep(1)

                    try:
                        await rest_msg.edit_text(f"⏸️ Відпочинок {i} сек")
                    except Exception as e:
                        print(f"⚠ Не вдалося оновити відпочинок: {e}")
                total_duration += 10

    save_workout_progress(user_id, workout, total_duration)
    achievements = check_achievements(user_id)
    achievement_text = "\n".join(
        [f"🏅 *Досягнення!* {a}" for a in achievements]) if achievements else ""
    await message.answer(
        f"✅ Завершено: {total_duration // 60} хв {total_duration % 60} сек\n{achievement_text}",
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    await state.clear()
    paused_workouts.pop(user_id, None)

@router.message(Form.workout, F.text == "⏹ Стоп")
async def stop_workout(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in paused_workouts:
        paused_workouts[user_id]["stopped"] = True
    else:
        await message.answer("⛔ Тренування не активне.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()

@router.message(Form.workout, F.text == "⏸️ Пауза")
async def pause_workout(message: types.Message):
    user_id = message.from_user.id
    if user_id in paused_workouts:
        paused_workouts[user_id]["paused"] = True
        await message.answer("⏸️ Тренування на паузі. Натисни ▶️ Продовжити для продовження.",
                             reply_markup=resume_buttons)
    else:
        await message.answer("⚠ Тренування зараз неактивне.")

@router.message(Form.workout, F.text == "▶️ Продовжити")
async def resume_workout(message: types.Message):
    user_id = message.from_user.id
    if user_id in paused_workouts and paused_workouts[user_id]["paused"]:
        paused_workouts[user_id]["paused"] = False
        await message.answer("▶️ Продовжуємо тренування!", reply_markup=control_buttons)
    else:
        await message.answer("⚠ Тренування зараз не на паузі.")

@router.callback_query(F.data.startswith("explain:"))
async def explain_exercise_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    exercise = callback.data.split("explain:")[1]
    video_url = video_links.get(exercise)

    # Ставимо паузу
    if user_id in paused_workouts:
        paused_workouts[user_id]["paused"] = True

    if video_url:
        await callback.message.answer(
            f"▶️ Пояснення до <b>{exercise}</b>:\n<a href='{video_url}'>{video_url}</a>",
            parse_mode="HTML",
            disable_web_page_preview=False,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="▶️ Продовжити вправу",
                    callback_data="resume_exercise"
                )
            ]])
        )
    else:
        await callback.message.answer("❌ Відео для цієї вправи поки що відсутнє.")
    await callback.answer()

@router.callback_query(F.data == "resume_exercise")
async def resume_exercise_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in paused_workouts:
        paused_workouts[user_id]["paused"] = False
        await callback.message.answer("▶️ Продовжуємо вправу!")
    await callback.answer()

@router.message(F.text == "📊 Прогрес")
async def view_progress(message: types.Message):
    workouts = get_progress(message.from_user.id)
    if workouts:
        response = "📜 *Історія тренувань:*\n\n"
        for w in workouts:
            timestamp = w.get("timestamp")
            duration = w.get("duration", 0)
            date_str = timestamp.strftime("%d.%m.%Y %H:%M") if timestamp else "невідомо"
            response += f"• {date_str} — {duration // 60} хв {duration % 60} сек\n"
        await message.answer(response, parse_mode="Markdown")
    else:
        await message.answer("🔕 У вас ще немає завершених тренувань.")

async def send_reminders(bot: Bot):
    users = get_all_users()
    for user in users:
        user_id = user["user_id"]
        workouts = get_progress(user_id)

        if not workouts:
            await bot.send_message(user_id, "👋 Ви ще не почали тренування. Введіть /workout, щоб розпочати!")
            continue

        last = workouts[0].get("timestamp")
        if last:
            last_dt = last.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if now - last_dt > timedelta(hours=24):
                await bot.send_message(
                    user_id,
                    "📢 Нагадування: ви не тренувалися понад 24 години. Пора повертатись у форму! 💪"
                )
