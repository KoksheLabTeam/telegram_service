from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL
import logging

router = Router()
logger = logging.getLogger(__name__)

# Определяем состояния для принятия/отклонения предложений
class OfferActionStates(StatesGroup):
    select_order = State()  # Выбор заказа
    select_offer = State()  # Выбор действия с предложением

# Точка входа для просмотра предложений
@router.message(F.text == "Посмотреть предложения")
async def start_view_offers(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer(
            "Только заказчики могут просматривать предложения.",
            reply_markup=get_main_keyboard(roles)
        )
        return

    try:
        # Получаем список заказов пользователя
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        pending_orders = [o for o in orders if o["status"] == "В_ожидании"]

        if not pending_orders:
            await message.answer(
                "У вас нет заказов со статусом 'В_ожидании', для которых можно просмотреть предложения.",
                reply_markup=get_main_keyboard(roles)
            )
            return

        orders_list = "\n".join([f"ID: {order['id']} - {order['title']}" for order in pending_orders])
        await message.answer(
            f"Ваши заказы в ожидании:\n{orders_list}\n\nВведите ID заказа, чтобы увидеть предложения:",
            reply_markup=get_main_keyboard(roles)
        )
        await state.set_state(OfferActionStates.select_order)
    except Exception as e:
        logger.error(f"Ошибка при загрузке заказов: {e}")
        await message.answer(
            f"Ошибка: {e}",
            reply_markup=get_main_keyboard(roles)
        )
        await state.clear()

# Обработка выбора заказа
@router.message(OfferActionStates.select_order)
async def process_order_selection(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        order_id = int(message.text.strip())
        # Проверяем, принадлежит ли заказ пользователю и имеет ли статус "В_ожидании"
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        selected_order = next(
            (order for order in orders if order["id"] == order_id and order["status"] == "В_ожидании"),
            None
        )
        if not selected_order:
            await message.answer(
                "Заказ не найден или не находится в статусе 'В_ожидании'.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
            return

        # Получаем предложения по заказу
        offers = await api_request("GET", f"{API_URL}order/{order_id}/offers", telegram_id)
        if not offers:
            await message.answer(
                f"По заказу ID {order_id} нет предложений.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
            return

        # Формируем список предложений с inline-кнопками
        offers_list = "\n\n".join([
            f"ID: {offer['id']}\n"
            f"Исполнитель: {offer['executor_id']}\n"
            f"Цена: {offer['price']} тенге\n"
            f"Время выполнения: {offer['estimated_time']} часов\n"
            f"Статус: {offer['status']}"
            for offer in offers if offer["status"] == "pending"  # Показываем только "pending"
        ])
        if not offers_list:
            await message.answer(
                f"По заказу ID {order_id} нет активных предложений.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
            return

        # Создаём inline-клавиатуру для каждого предложения
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[])
        for offer in offers:
            if offer["status"] == "pending":
                inline_kb.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=f"Принять (ID: {offer['id']})",
                        callback_data=f"accept_offer_{order_id}_{offer['id']}"
                    ),
                    InlineKeyboardButton(
                        text=f"Отклонить (ID: {offer['id']})",
                        callback_data=f"reject_offer_{order_id}_{offer['id']}"
                    )
                ])

        await message.answer(
            f"Предложения по заказу ID {order_id}:\n{offers_list}",
            reply_markup=inline_kb
        )
        await state.update_data(order_id=order_id)
        await state.set_state(OfferActionStates.select_offer)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
    except Exception as e:
        logger.error(f"Ошибка при выборе заказа: {e}")
        await message.answer(
            f"Ошибка: {e}",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()

# Обработка callback-запросов для принятия/отклонения предложений
@router.callback_query(F.data.startswith("accept_offer_"))
async def process_accept_offer(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    try:
        _, order_id, offer_id = callback.data.split("_")
        order_id = int(order_id)
        offer_id = int(offer_id)

        # Отправляем запрос на принятие предложения
        updated_order = await api_request(
            "POST",
            f"{API_URL}order/{order_id}/offers/{offer_id}/accept",
            telegram_id
        )
        await callback.message.edit_text(
            f"Предложение ID {offer_id} по заказу ID {order_id} успешно принято!\n"
            f"Статус заказа: {updated_order['status']}",
            reply_markup=None
        )
        await callback.answer("Предложение принято!")
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при принятии предложения: {e}")
        await callback.message.edit_text(
            f"Ошибка при принятии предложения: {e}",
            reply_markup=None
        )
        await callback.answer("Ошибка!")
        await state.clear()

@router.callback_query(F.data.startswith("reject_offer_"))
async def process_reject_offer(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    try:
        _, order_id, offer_id = callback.data.split("_")
        order_id = int(order_id)
        offer_id = int(offer_id)

        # Отправляем запрос на отклонение предложения
        updated_offer = await api_request(
            "POST",
            f"{API_URL}order/{order_id}/offers/{offer_id}/reject",
            telegram_id
        )
        await callback.message.edit_text(
            f"Предложение ID {offer_id} по заказу ID {order_id} успешно отклонено!\n"
            f"Статус предложения: {updated_offer['status']}",
            reply_markup=None
        )
        await callback.answer("Предложение отклонено!")
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при отклонении предложения: {e}")
        await callback.message.edit_text(
            f"Ошибка при отклонении предложения: {e}",
            reply_markup=None
        )
        await callback.answer("Ошибка!")
        await state.clear()
