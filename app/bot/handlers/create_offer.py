from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.config import API_URL
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.bot.handlers.start import get_main_keyboard  # Импортируем из start.py
import logging

router = Router()
logger = logging.getLogger(__name__)


class CreateOffer(StatesGroup):
    price = State()
    comment = State()


@router.message(F.text == "Создать предложение")
async def start_create_offer(message: Message, state: FSMContext):
    logger.info(f"Команда 'Создать предложение' от пользователя {message.from_user.id}")
    telegram_id = get_user_telegram_id(message)
    try:
        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
        if not user["is_executor"]:
            await message.answer("Только исполнители могут создавать предложения.", reply_markup=get_main_keyboard(
                {"is_executor": False, "is_admin": telegram_id == 704342630}))
            return

        orders = await api_request("GET", f"{API_URL}order/available", telegram_id)
        if not orders:
            await message.answer("Нет доступных заказов для создания предложений.", reply_markup=get_main_keyboard(
                {"is_executor": True, "is_admin": telegram_id == 704342630}))
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                                            [InlineKeyboardButton(
                                                                text=f"Заказ {order['id']} - {order['title']}",
                                                                callback_data=f"offer_{order['id']}")]
                                                            for order in orders
                                                        ] + [
                                                            [InlineKeyboardButton(text="Назад", callback_data="back")]])
        await message.answer("Выберите заказ для создания предложения:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в start_create_offer: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(
            {"is_executor": False, "is_admin": telegram_id == 704342630}))


@router.callback_query(F.data.startswith("offer_"))
async def process_order_selection(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Обработчик process_order_selection вызван для telegram_id={callback.from_user.id}")
    order_id = int(callback.data.split("_")[1])
    await state.update_data(order_id=order_id)
    await callback.message.answer("Введите вашу цену для предложения (в тенге):")
    await state.set_state(CreateOffer.price)
    await callback.answer()


@router.message(CreateOffer.price)
async def process_price(message: Message, state: FSMContext):
    logger.info(f"Обработчик process_price вызван для telegram_id={message.from_user.id}")
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await message.answer("Введите комментарий к предложению (или нажмите /skip для пропуска):")
        await state.set_state(CreateOffer.comment)
    except ValueError:
        await message.answer("Пожалуйста, введите корректную цену (число).")


@router.message(CreateOffer.comment)
async def process_comment(message: Message, state: FSMContext):
    logger.info(f"Обработчик process_comment вызван для telegram_id={message.from_user.id}")
    telegram_id = get_user_telegram_id(message)
    data = await state.get_data()
    order_id = data["order_id"]
    price = data["price"]
    comment = message.text if message.text != "/skip" else ""

    try:
        offer_data = {
            "order_id": order_id,
            "price": price,
            "comment": comment
        }
        await api_request("POST", f"{API_URL}offer/", telegram_id, data=offer_data)
        await message.answer("Предложение успешно создано!", reply_markup=get_main_keyboard(
            {"is_executor": True, "is_admin": telegram_id == 704342630}))
    except Exception as e:
        logger.error(f"Ошибка в process_comment: {e}")
        await message.answer(f"Ошибка создания предложения: {e}", reply_markup=get_main_keyboard(
            {"is_executor": True, "is_admin": telegram_id == 704342630}))
    await state.clear()


@router.message(F.text == "/skip", CreateOffer.comment)
async def skip_comment(message: Message, state: FSMContext):
    logger.info(f"Обработчик skip_comment вызван для telegram_id={message.from_user.id}")
    await process_comment(message, state)