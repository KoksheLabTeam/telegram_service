import asyncio
from aiogram import Bot, Dispatcher
from app.bot.config import BOT_TOKEN
from app.bot.handlers import start, create_order, profile, orders, admin, cities, categories, switch_role

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(start.router)
dp.include_router(create_order.router)
dp.include_router(profile.router)
dp.include_router(orders.router)
dp.include_router(admin.router)
dp.include_router(cities.router)
dp.include_router(categories.router)
dp.include_router(switch_role.router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())