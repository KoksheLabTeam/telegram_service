from aiogram import Bot, Dispatcher
from app.bot.config import BOT_TOKEN, ADMIN_TELEGRAM_ID
from app.bot.handlers import (
    admin_panel_router, manage_users_router, manage_orders_router, manage_cities_router, manage_categories_router,
    create_order_router, customer_orders_router, review_router,
    create_offer_router, complete_order_router, manage_offers_router,
    start_router, profile_router, switch_role_router
)
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключение всех роутеров
dp.include_router(start_router)
dp.include_router(profile_router)
dp.include_router(switch_role_router)
dp.include_router(admin_panel_router)
dp.include_router(manage_users_router)
dp.include_router(manage_orders_router)
dp.include_router(manage_cities_router)
dp.include_router(manage_categories_router)
dp.include_router(create_order_router)
dp.include_router(customer_orders_router)
dp.include_router(review_router)
dp.include_router(create_offer_router)
dp.include_router(manage_offers_router)
dp.include_router(complete_order_router)

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