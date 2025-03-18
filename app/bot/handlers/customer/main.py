from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL
from app.bot.handlers.customer.orders import start_create_order  # Импортируем функцию
import logging


router = Router()
logger = logging.getLogger(__name__)

class ReviewStates(StatesGroup):
    select_order = State()
    rating = State()
    comment = State()

@router.message(F.text == "Создать заказ")
async def create_order_entrypoint(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles.get("is_customer"):
        await message.answer(
            "Эта функция доступна только для заказчиков.",
            reply_markup=get_main_keyboard(roles)
        )
        return
    try:
        await start_create_order(message, state)
    except Exception as e:
        logger.error(f"Ошибка при создании заказа: {e}")
        await message.answer(
            f"Не удалось начать создание заказа: {e}",
            reply_markup=get_main_keyboard(roles)
        )

@router.message(F.text == "Список заказов")
async def list_orders(message: Message):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        if not orders:
            await message.answer("У вас нет заказов.", reply_markup=get_main_keyboard(roles))
            return
        response = "Ваши заказы:\n\n"
        for order in orders:
            status = {"В_ожидании": "Ожидает", "В_прогрессе": "В процессе", "Выполнен": "Завершён", "Отменен": "Отменён"}.get(order["status"], order["status"])
            response += f"ID: {order['id']} - {order['title']} ({status})\n"
        await message.answer(response, reply_markup=get_main_keyboard(roles))
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

@router.message(F.text == "Написать отзыв")
async def review_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer("Только заказчики могут писать отзывы.", reply_markup=get_main_keyboard(roles))
        return
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        completed_orders = [o for o in orders if o["status"] == "Выполнен" and o["customer_id"] == telegram_id]
        if not completed_orders:
            await message.answer("У вас нет завершённых заказов для отзыва.", reply_markup=get_main_keyboard(roles))
            return
        response = "Завершённые заказы:\n\n"
        for order in completed_orders:
            response += f"ID: {order['id']} - {order['title']}\n"
        await message.answer(response + "\nВведите ID заказа для отзыва:")
        await state.set_state(ReviewStates.select_order)
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

@router.message(ReviewStates.select_order)
async def review_rating(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        order_id = int(message.text.strip())
        order = await api_request("GET", f"{API_URL}order/{order_id}", telegram_id)
        if order["status"] != "Выполнен" or order["customer_id"] != telegram_id:
            await message.answer("Этот заказ нельзя оценить.", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
            await state.clear()
            return
        await state.update_data(order_id=order_id, target_id=order["executor_id"])
        await message.answer("Введите рейтинг (от 1 до 5):")
        await state.set_state(ReviewStates.rating)
    except ValueError:
        await message.answer("Ошибка: Введите корректный ID заказа")
    except Exception as e:
        logger.error(f"Ошибка выбора заказа: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

@router.message(ReviewStates.rating)
async def review_comment(message: Message, state: FSMContext):
    try:
        rating = int(message.text.strip())
        if not 1 <= rating <= 5:
            raise ValueError("Рейтинг должен быть от 1 до 5")
        await state.update_data(rating=rating)
        await message.answer("Введите комментарий (или пропустите, нажав Enter):")
        await state.set_state(ReviewStates.comment)
    except ValueError as e:
        await message.answer(f"Ошибка: {e if str(e) != 'Рейтинг должен быть от 1 до 5' else 'Введите число от 1 до 5'}")

@router.message(ReviewStates.comment)
async def review_finish(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    comment = message.text.strip() if message.text.strip() else None
    data = await state.get_data()
    review_data = {
        "order_id": data["order_id"],
        "target_id": data["target_id"],
        "rating": data["rating"],
        "comment": comment
    }
    try:
        review = await api_request("POST", f"{API_URL}review/", telegram_id, data=review_data)
        await message.answer(f"Отзыв успешно оставлен для заказа ID {review['order_id']}!",
                             reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка создания отзыва: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()