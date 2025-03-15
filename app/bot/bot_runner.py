from aiogram import Bot, Dispatcher
from app.bot.config import BOT_TOKEN, ADMIN_TELEGRAM_ID
from app.bot.handlers import start_router, create_order_router, switch_role_router, admin_router, create_offer_router, \
    manage_offers_router
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


dp.include_router(start_router)
dp.include_router(create_order_router)
dp.include_router(switch_role_router)
dp.include_router(admin_router)
dp.include_router(create_offer_router)
dp.include_router(manage_offers_router)


async def main():
    logger.info(f"Бот запущен с токеном: {BOT_TOKEN[:10]}...")
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot info: {bot_info.username}, ID: {bot_info.id}")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске polling: {e}")
        raise
    finally:
        await bot.session.close()  # Закрываем сессию


if __name__ == "__main__":
    asyncio.run(main())
