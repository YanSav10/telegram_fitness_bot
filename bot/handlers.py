import asyncio
import re
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
from bot.buttons import goal_buttons, control_buttons, resume_buttons, progress_buttons
from bot.workouts import workout_plans
from bot.video_links import video_links
from aiogram.exceptions import TelegramBadRequest

router = Router()

class Form(StatesGroup):
    goal = State()
    height = State()
    weight = State()
    age = State()
    workout_choice = State()
    duration = State()
    rest = State()
    workout = State()

paused_workouts = {}

def get_explanation_button(exercise_name: str):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔍 Пояснення",
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
        await message.answer("⏱ Введи *тривалість вправ* у секундах (від 5 до 120):", parse_mode="Markdown")
        await state.set_state(Form.duration)
    else:
        await message.answer("❌ Такого тренування немає. Спробуй ще раз.")

@router.message(Form.duration)
async def set_custom_duration(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("🚫 Введи число від 5 до 120.")
        return
    duration = int(message.text)
    if 5 <= duration <= 120:
        await state.update_data(custom_duration=duration)
        await message.answer("🔄 Тепер введи *тривалість відпочинку* у секундах (від 5 до 120):", parse_mode="Markdown")
        await state.set_state(Form.rest)
    else:
        await message.answer("🚫 Число має бути від 5 до 120.")

@router.message(Form.rest)
async def set_custom_rest(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("🚫 Введи число від 5 до 120.")
        return
    rest = int(message.text)
    if 5 <= rest <= 120:
        await state.update_data(custom_rest=rest)
        data = await state.get_data()
        workout = data["workout"]
        await message.answer(f"{workout}\n🔴 Натисни Старт для початку", reply_markup=control_buttons)
        await state.set_state(Form.workout)
    else:
        await message.answer("🚫 Число має бути від 5 до 120.")

@router.message(Form.workout, F.text == "🔴 Старт")
async def start_timer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    workout = data["workout"]
    user_id = data["user_id"]
    exercise_duration = data.get("custom_duration", 30)
    rest_duration = data.get("custom_rest", 10)

    exercises = re.findall(r"✅ ([^\n]+)", workout)
    total_duration = 0

    paused_workouts[user_id] = {
        "paused": False,
        "stopped": False,
        "remaining_time": 0,
        "remaining_rest": 0,
        "mode": None,
        "message_id": None,
        "resume_requested": False
    }

    for idx, exercise in enumerate(exercises):
        await message.answer(f"🔹 <b>{exercise}</b>", parse_mode="HTML", reply_markup=get_explanation_button(exercise))
        remaining = paused_workouts[user_id]["remaining_time"] or exercise_duration
        paused_workouts[user_id].update({"mode": "exercise"})

        timer_msg = await message.answer(f"⏱️ Залишилось: {remaining} сек", parse_mode="HTML")
        paused_workouts[user_id]["message_id"] = timer_msg.message_id

        while remaining > 0:
            await asyncio.sleep(1)

            if paused_workouts[user_id]["stopped"]:
                await message.answer("⛔ Тренування зупинено.", reply_markup=types.ReplyKeyboardRemove())
                await state.clear()
                paused_workouts.pop(user_id, None)
                return

            if paused_workouts[user_id]["paused"]:
                paused_workouts[user_id]["remaining_time"] = remaining
                while paused_workouts[user_id]["paused"] and not paused_workouts[user_id].get("resume_requested"):
                    await asyncio.sleep(0.5)
                paused_workouts[user_id]["resume_requested"] = False
                continue

            remaining -= 1
            try:
                await timer_msg.edit_text(f"⏱️ Залишилось: {remaining} сек", parse_mode="HTML")
            except TelegramBadRequest:
                pass

        paused_workouts[user_id]["remaining_time"] = 0
        total_duration += exercise_duration

        # Відпочинок
        if idx < len(exercises) - 1:
            rest = paused_workouts[user_id]["remaining_rest"] or rest_duration
            paused_workouts[user_id].update({"mode": "rest"})
            rest_msg = await message.answer(f"⏸️ Відпочинок {rest} сек", parse_mode="HTML")
            paused_workouts[user_id]["message_id"] = rest_msg.message_id

            while rest > 0:
                await asyncio.sleep(1)

                if paused_workouts[user_id]["stopped"]:
                    await message.answer("⛔ Тренування зупинено.", reply_markup=types.ReplyKeyboardRemove())
                    await state.clear()
                    paused_workouts.pop(user_id, None)
                    return

                if paused_workouts[user_id]["paused"]:
                    paused_workouts[user_id]["remaining_rest"] = rest
                    while paused_workouts[user_id]["paused"] and not paused_workouts[user_id].get("resume_requested"):
                        await asyncio.sleep(0.5)
                    paused_workouts[user_id]["resume_requested"] = False
                    continue

                rest -= 1
                try:
                    await rest_msg.edit_text(f"⏸️ Відпочинок {rest} сек")
                except TelegramBadRequest:
                    pass

            paused_workouts[user_id]["remaining_rest"] = 0
            total_duration += rest_duration

    save_workout_progress(user_id, workout, total_duration)
    achievements = check_achievements(user_id)
    achievement_text = "\n".join([f"🏅 *Досягнення!* {a}" for a in achievements]) if achievements else ""
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
        await message.answer(
            "⏸️ Тренування на паузі. Натисни ▶️ Продовжити для продовження.",
            reply_markup=resume_buttons
        )
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=paused_workouts[user_id]["message_id"]
            )
        except TelegramBadRequest:
            pass
    else:
        await message.answer("⚠ Тренування зараз неактивне.")

@router.message(Form.workout, F.text == "▶️ Продовжити")
async def resume_workout(message: types.Message):
    user_id = message.from_user.id
    if user_id not in paused_workouts or not paused_workouts[user_id]["paused"]:
        await message.answer("⚠ Тренування зараз не на паузі.")
        return

    paused_workouts[user_id]["paused"] = False
    paused_workouts[user_id]["resume_requested"] = True

    try:
        msg_id = paused_workouts[user_id].get("message_id")
        if msg_id:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
    except TelegramBadRequest:
        pass

    # Після видалення старого повідомлення створюємо нове
    mode = paused_workouts[user_id].get("mode")
    remaining = paused_workouts[user_id].get("remaining_time" if mode == "exercise" else "remaining_rest", 0)

    text = f"⏱️ Залишилось: {remaining} сек" if mode == "exercise" else f"⏸️ Відпочинок {remaining} сек"
    timer_msg = await message.answer(text, parse_mode="HTML")
    paused_workouts[user_id]["message_id"] = timer_msg.message_id

    await message.answer("▶️ Продовжуємо тренування!", reply_markup=control_buttons)

    # 🔁 Динамічне оновлення
    while remaining > 0:
        await asyncio.sleep(1)

        if paused_workouts[user_id]["paused"]:
            if mode == "exercise":
                paused_workouts[user_id]["remaining_time"] = remaining
            else:
                paused_workouts[user_id]["remaining_rest"] = remaining
            return

        if paused_workouts[user_id]["stopped"]:
            await message.answer("⛔ Тренування зупинено.", reply_markup=types.ReplyKeyboardRemove())
            paused_workouts.pop(user_id, None)
            return

        remaining -= 1
        try:
            await timer_msg.edit_text(
                f"⏱️ Залишилось: {remaining} сек" if mode == "exercise" else f"⏸️ Відпочинок {remaining} сек",
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            pass

    # Скидання лічильника
    if mode == "exercise":
        paused_workouts[user_id]["remaining_time"] = 0
    else:
        paused_workouts[user_id]["remaining_rest"] = 0

@router.callback_query(F.data.startswith("explain:"))
async def explain_exercise_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    exercise = callback.data.split("explain:")[1]
    video_url = video_links.get(exercise)

    if user_id in paused_workouts:
        paused_workouts[user_id]["paused"] = True
        try:
            msg_id = paused_workouts[user_id].get("message_id")
            if msg_id:
                await callback.message.bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=msg_id
                )
        except TelegramBadRequest:
            pass

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
    if user_id not in paused_workouts:
        await callback.answer("⚠ Тренування не знайдено.")
        return

    paused_workouts[user_id]["paused"] = False
    paused_workouts[user_id]["resume_requested"] = True

    try:
        msg_id = paused_workouts[user_id].get("message_id")
        if msg_id:
            await callback.message.bot.delete_message(chat_id=callback.message.chat.id, message_id=msg_id)
    except TelegramBadRequest:
        pass

    mode = paused_workouts[user_id].get("mode")
    remaining = paused_workouts[user_id].get("remaining_time" if mode == "exercise" else "remaining_rest", 0)

    text = f"⏱️ Залишилось: {remaining} сек" if mode == "exercise" else f"⏸️ Відпочинок {remaining} сек"
    timer_msg = await callback.message.answer(text, parse_mode="HTML")
    paused_workouts[user_id]["message_id"] = timer_msg.message_id

    await callback.message.answer("▶️ Продовжуємо вправу!", reply_markup=control_buttons)
    await callback.answer()

    # 🔁 Динамічне оновлення
    while remaining > 0:
        await asyncio.sleep(1)

        if paused_workouts[user_id]["paused"]:
            if mode == "exercise":
                paused_workouts[user_id]["remaining_time"] = remaining
            else:
                paused_workouts[user_id]["remaining_rest"] = remaining
            return

        if paused_workouts[user_id]["stopped"]:
            await callback.message.answer("⛔ Тренування зупинено.", reply_markup=types.ReplyKeyboardRemove())
            paused_workouts.pop(user_id, None)
            return

        remaining -= 1
        try:
            await timer_msg.edit_text(
                f"⏱️ Залишилось: {remaining} сек" if mode == "exercise" else f"⏸️ Відпочинок {remaining} сек",
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            pass

    if mode == "exercise":
        paused_workouts[user_id]["remaining_time"] = 0
    else:
        paused_workouts[user_id]["remaining_rest"] = 0

@router.message(Command("progress"))
async def choose_progress_period(message: types.Message):
    await message.answer("🔎 Обери період для перегляду прогресу:", reply_markup=progress_buttons)

@router.message(F.text.in_([
    "📅 7 днів", "📅 14 днів", "📅 30 днів",
    "📆 6 місяців", "📅 1 рік", "📖 Увесь час"
]))
async def show_progress_by_period(message: types.Message):
    from datetime import datetime, timedelta
    from collections import Counter

    def format_time(mins, secs):
        if mins == 0 and secs == 0:
            return "—"
        if mins >= 60:
            hours, mins = divmod(mins, 60)
            return f"{hours} год {mins} хв {secs} сек"
        else:
            return f"{mins} хв {secs} сек"

    user_id = message.from_user.id
    workouts = get_progress(user_id)
    if not workouts:
        await message.answer("❌ У вас ще немає завершених тренувань.")
        return

    now = datetime.now()
    period_text = message.text
    periods = {
        "📅 7 днів": timedelta(days=7),
        "📅 14 днів": timedelta(days=14),
        "📅 30 днів": timedelta(days=30),
        "📆 6 місяців": timedelta(days=182),
        "📅 1 рік": timedelta(days=365),
        "📖 Увесь час": None
    }

    cutoff = now - periods[period_text] if periods[period_text] else None

    filtered = [
        w for w in workouts
        if w.get("timestamp") and isinstance(w.get("timestamp"), datetime)
        and (not cutoff or w["timestamp"].replace(tzinfo=None) >= cutoff)
    ]

    if not filtered:
        await message.answer("ℹ️ За цей період тренувань не було.")
        return

    durations = [w.get("duration", 0) for w in filtered if w.get("duration", 0) > 0]
    total_duration = sum(durations)
    total_workouts = len(durations)
    avg_duration = total_duration // total_workouts if total_workouts else 0
    min_duration = min(durations) if durations else 0
    max_duration = max(durations) if durations else 0

    total_min, total_sec = divmod(total_duration, 60)
    avg_min, avg_sec = divmod(avg_duration, 60)
    min_min, min_sec = divmod(min_duration, 60)
    max_min, max_sec = divmod(max_duration, 60)

    first = filtered[-1]["timestamp"]
    last = filtered[0]["timestamp"]

    active_days = sorted(set(w["timestamp"].date() for w in filtered))
    if cutoff:
        period_days = (now.date() - cutoff.date()).days
    else:
        period_days = (last.date() - first.date()).days
    period_days = max(period_days, 1)
    active_day_count = len(active_days)
    active_percent = round((active_day_count / period_days) * 100)

    # 🔥 Рівень активності
    active_days_score = active_day_count / period_days
    workouts_per_day = total_workouts / period_days
    workouts_score = min(workouts_per_day, 1.0)

    total_minutes = total_duration / 60
    total_minutes_score = min(total_minutes / (period_days * 10), 1.0)

    avg_minutes = avg_duration / 60
    avg_minutes_score_for_activity = min(avg_minutes / 20, 1.0)

    score = (
        0.4 * active_days_score +
        0.2 * workouts_score +
        0.2 * total_minutes_score +
        0.2 * avg_minutes_score_for_activity
    )

    if score >= 0.75:
        activity = "🔵 Висока"
    elif score >= 0.4:
        activity = "🟡 Середня"
    else:
        activity = "🔴 Низька"

    # 📈 Коефіцієнт стабільності
    avg_minutes_per_active_day = total_minutes / active_day_count if active_day_count else 0
    avg_minutes_score = min(avg_minutes_per_active_day / 20, 1.0)
    stability = round(active_days_score * avg_minutes_score, 2)

    if stability >= 0.7:
        stability_level = "🔵 Висока"
    elif stability >= 0.4:
        stability_level = "🟡 Середня"
    else:
        stability_level = "🔴 Низька"

    # ➕ Додаткова аналітика
    weekday_map = {
        0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Нд"
    }
    weekdays = [w["timestamp"].weekday() for w in filtered]
    weekday_counts = Counter(weekdays)
    top_days = ", ".join(weekday_map[d] for d, _ in weekday_counts.most_common(2)) if weekday_counts else "—"

    streak = max_streak = 1
    for i in range(1, len(active_days)):
        if (active_days[i] - active_days[i - 1]).days == 1:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 1
    max_streak = max_streak if active_day_count > 0 else 0

    max_gap = 0
    for i in range(1, len(active_days)):
        gap = (active_days[i] - active_days[i - 1]).days - 1
        if gap > max_gap:
            max_gap = gap

    short_count = sum(1 for d in durations if d <= 5 * 60)
    short_percent = round((short_count / total_workouts) * 100) if total_workouts else 0

    await message.answer(
        f"📊 <b>Прогрес за {period_text}:</b>\n\n"
        f"🔁 <b>Кількість тренувань:</b> {total_workouts}\n"
        f"📅 <b>Днів з тренуваннями:</b> {active_day_count} з {period_days} днів ({active_percent}%)\n"
        f"⏱️ <b>Загальна тривалість:</b> {format_time(total_min, total_sec)}\n"
        f"📊 <b>Середня тривалість:</b> {format_time(avg_min, avg_sec)}\n"
        f"🔸 <b>Найкоротше тренування:</b> {format_time(min_min, min_sec)}\n"
        f"🔹 <b>Найдовше тренування:</b> {format_time(max_min, max_sec)}\n"
        f"🗓️ <b>Перше тренування:</b> {first.strftime('%d.%m.%Y %H:%M')}\n"
        f"📅 <b>Останнє тренування:</b> {last.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔥 <b>Рівень активності:</b> {activity} ({round(score, 2)})\n\n"
        f"📆 <b>Найактивніші дні:</b> {top_days}\n"
        f"🔁 <b>Макс. стрік:</b> {max_streak} днів поспіль\n"
        f"⛔ <b>Макс. перерва:</b> {max_gap} днів без тренувань\n"
        f"🤏 <b>Короткі тренування:</b> {short_percent}%\n"
        f"📈 <b>Коефіцієнт стабільності:</b> {stability} ({stability_level})",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="ℹ️ Пояснення метрик", callback_data="explain_metrics")]
            ]
        )
    )

@router.callback_query(F.data == "explain_metrics")
async def explain_metrics_callback(callback: types.CallbackQuery):
    await callback.message.answer(
        text=(
            "<b>📊 Пояснення всіх метрик:</b>\n\n"

            "🔁 <b>Кількість тренувань</b> — скільки тренувань виконано за період.\n"
            "📅 <b>Днів з тренуваннями</b> — у скількох днях були хоча б одне тренування.\n\n"

            "⏱️ <b>Загальна тривалість</b> — сумарний час усіх тренувань.\n"
            "📊 <b>Середня тривалість</b> — середній час одного тренування.\n"
            "🔸 <b>Найкоротше</b> — найменший за тривалістю запис.\n"
            "🔹 <b>Найдовше</b> — найдовший за тривалістю запис.\n\n"

            "🗓️ <b>Перше тренування</b> — дата найстарішого тренування у періоді.\n"
            "📅 <b>Останнє тренування</b> — дата останнього тренування.\n\n"

            "🔥 <b>Рівень активності</b> — наскільки часто та інтенсивно ви тренувались:\n"
            "🔵 Висока  🟡 Середня  🔴 Низька\n\n"

            "📈 <b>Коефіцієнт стабільності</b> — наскільки регулярно й рівномірно ви тренувались:\n"
            "🔵 Висока  🟡 Середня  🔴 Низька\n\n"

            "📆 <b>Найактивніші дні</b> — дні тижня з найбільшою кількістю тренувань.\n"
            "🔁 <b>Макс. стрік</b> — найдовша серія днів поспіль з тренуваннями.\n"
            "⛔ <b>Макс. перерва</b> — найбільший проміжок без тренувань.\n"
            "🤏 <b>Короткі тренування</b> — відсоток тренувань менше 5 хв.\n"
        ),
        parse_mode="HTML"
    )
    await callback.answer()

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
