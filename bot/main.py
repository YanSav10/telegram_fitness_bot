import asyncio
import logging
from aiogram import Bot, Dispatcher
from .config import BOT_TOKEN
from .handlers import router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .handlers import send_reminders

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # 📆 Запуск щоденного нагадування о 10:00 за Києвом (UTC+3)
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(send_reminders, "cron", hour=10, args=[bot])
    scheduler.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
