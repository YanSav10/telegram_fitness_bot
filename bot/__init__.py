from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from bot.config import BOT_TOKEN

# Створюємо екземпляр бота з правильними параметрами
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

# Диспетчер (з підтримкою FSM)
dp = Dispatcher(storage=MemoryStorage())
