from aiogram import Bot, Dispatcher
from app.bot.config import BOT_TOKEN, ADMIN_TELEGRAM_ID
from app.bot.handlers.start import router as start_router
from app.bot.handlers.switch_role import router as switch_role_router
from app.bot.handlers.admin import admin_routers
from app.bot.handlers.customer import customer_routers
from app.bot.handlers.executor import executor_routers
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключаем роутеры
dp.include_router(start_router)
dp.include_router(switch_role_router)
for admin_router in admin_routers:
    dp.include_router(admin_router)
for customer_router in customer_routers:
    dp.include_router(customer_router)
for executor_router in executor_routers:
    dp.include_router(executor_router)

async def main():
    logger.info(f"Бот запущен с токеном: {BOT_TOKEN[:10]}...")
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot info: {bot_info.username}, ID: {bot_info.id}")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске polling: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())