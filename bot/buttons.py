from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Кнопки для вибору мети
goal_buttons = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔥 Схуднення")],
        [KeyboardButton(text="💪 Набір маси")],
        [KeyboardButton(text="🏃 Витривалість")],
        [KeyboardButton(text="⚡ Сила")]
    ],
    resize_keyboard=True
)

# Кнопки під час тренування
control_buttons = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔴 Старт")],
        [KeyboardButton(text="⏸️ Пауза"), KeyboardButton(text="⏹ Стоп")]
    ],
    resize_keyboard=True
)

# Кнопки під час паузи
resume_buttons = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="▶️ Продовжити"), KeyboardButton(text="⏹ Стоп")]
    ],
    resize_keyboard=True
)

progress_buttons = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 7 днів"), KeyboardButton(text="📅 14 днів")],
        [KeyboardButton(text="📅 30 днів"), KeyboardButton(text="📆 6 місяців")],
        [KeyboardButton(text="📅 1 рік"), KeyboardButton(text="📖 Увесь час")]
    ],
    resize_keyboard=True
)
