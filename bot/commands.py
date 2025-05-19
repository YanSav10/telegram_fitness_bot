from aiogram import Bot
from aiogram.types import BotCommand

async def set_default_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🔁 Запустити бота"),
        BotCommand(command="workout", description="🏋 Почати тренування"),
        BotCommand(command="progress", description="📊 Переглянути прогрес")
    ]
    await bot.set_my_commands(commands)
