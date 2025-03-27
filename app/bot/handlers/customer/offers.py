from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL
import logging

router = Router()
logger = logging.getLogger(__name__)


# Определяем состояния для работы с предложениями
class OfferActionStates(StatesGroup):
    select_order = State()  # Выбор заказа для просмотра предложений


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
        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
        user_id = user["id"]
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        pending_orders = [o for o in orders if o["status"] == "PENDING" and o["customer_id"] == user_id]
        logger.info(f"Заказы в статусе PENDING для пользователя {telegram_id} (user_id: {user_id}): {pending_orders}")

        if not pending_orders:
            await message.answer(
                "У вас нет заказов в статусе 'PENDING', для которых можно просмотреть предложения.",
                reply_markup=get_main_keyboard(roles)
            )
            return

        orders_list = "\n".join([f"ID: {order['id']} - {order['title']}" for order in pending_orders])
        await message.answer(
            f"Ваши заказы в статусе PENDING:\n{orders_list}\n\nВведите ID заказа, чтобы увидеть предложения:",
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


@router.message(OfferActionStates.select_order)
async def process_order_selection(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    try:
        order_id = int(message.text.strip())
        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
        user_id = user["id"]
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        selected_order = next(
            (order for order in orders if
             order["id"] == order_id and order["status"] == "PENDING" and order["customer_id"] == user_id),
            None
        )

        if not selected_order:
            await message.answer(
                "Заказ не найден, не принадлежит вам или не находится в статусе 'PENDING'.",
                reply_markup=get_main_keyboard(roles)
            )
            await state.clear()
            return

        offers = await api_request("GET", f"{API_URL}order/{order_id}/offers", telegram_id)
        logger.info(f"Полученные предложения для заказа {order_id}: {offers}")

        if not offers:
            await message.answer(
                f"По заказу ID {order_id} нет предложений.",
                reply_markup=get_main_keyboard(roles)
            )
            await state.clear()
            return

        pending_offers = [offer for offer in offers if offer["status"] == "pending"]
        if not pending_offers:
            await message.answer(
                f"По заказу ID {order_id} нет активных предложений в статусе 'pending'.",
                reply_markup=get_main_keyboard(roles)
            )
            await state.clear()
            return

        offers_list = "\n\n".join([
            f"ID: {offer['id']}\n"
            f"Исполнитель: {offer['executor_id']}\n"
            f"Цена: {offer['price']} тенге\n"
            f"Время выполнения: {offer['estimated_time']} часов\n"
            f"Статус: {offer['status']}"
            for offer in pending_offers
        ])

        inline_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Принять (ID: {offer['id']})",
                    callback_data=f"accept_offer_{order_id}_{offer['id']}"
                ),
                InlineKeyboardButton(
                    text=f"Отклонить (ID: {offer['id']})",
                    callback_data=f"reject_offer_{order_id}_{offer['id']}"
                )
            ] for offer in pending_offers
        ])

        await message.answer(
            f"Предложения по заказу ID {order_id}:\n{offers_list}",
            reply_markup=inline_kb
        )
        await state.clear()  # Сбрасываем состояние после отображения предложений
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
    except Exception as e:
        logger.error(f"Ошибка при выборе заказа: {e}")
        await message.answer(
            f"Ошибка: {e}",
            reply_markup=get_main_keyboard(roles)
        )
        await state.clear()


# Обработка принятия предложения
@router.callback_query(F.data.startswith("accept_offer_"))
async def process_accept_offer(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await callback.message.edit_text("Только заказчики могут принимать предложения.", reply_markup=None)
        await callback.answer("Доступ запрещён!")
        return

    try:
        _, order_id, offer_id = callback.data.split("_")
        order_id = int(order_id)
        offer_id = int(offer_id)

        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
        user_id = user["id"]
        order = await api_request("GET", f"{API_URL}order/{order_id}", telegram_id)

        if order["customer_id"] != user_id or order["status"] != "PENDING":
            await callback.message.edit_text(
                "Заказ не найден или недоступен для принятия предложений.",
                reply_markup=None
            )
            await callback.answer("Ошибка!")
            return

        updated_order = await api_request(
            "POST",
            f"{API_URL}order/{order_id}/offers/{offer_id}/accept",
            telegram_id
        )
        logger.info(
            f"Предложение {offer_id} для заказа {order_id} принято пользователем {telegram_id}: {updated_order}")

        await callback.message.edit_text(
            f"Предложение ID {offer_id} по заказу ID {order_id} успешно принято!\n"
            f"Статус заказа: {updated_order['status']}",
            reply_markup=None
        )
        await callback.answer("Предложение принято!")
    except Exception as e:
        logger.error(f"Ошибка при принятии предложения: {e}")
        await callback.message.edit_text(
            f"Ошибка при принятии предложения: {e}",
            reply_markup=None
        )
        await callback.answer("Ошибка!")


# Обработка отклонения предложения
@router.callback_query(F.data.startswith("reject_offer_"))
async def process_reject_offer(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await callback.message.edit_text("Только заказчики могут отклонять предложения.", reply_markup=None)
        await callback.answer("Доступ запрещён!")
        return

    try:
        _, order_id, offer_id = callback.data.split("_")
        order_id = int(order_id)
        offer_id = int(offer_id)

        user = await api_request("GET", f"{API_URL}user/by_telegram_id/{telegram_id}", telegram_id)
        user_id = user["id"]
        order = await api_request("GET", f"{API_URL}order/{order_id}", telegram_id)

        if order["customer_id"] != user_id or order["status"] != "PENDING":
            await callback.message.edit_text(
                "Заказ не найден или недоступен для отклонения предложений.",
                reply_markup=None
            )
            await callback.answer("Ошибка!")
            return

        updated_offer = await api_request(
            "POST",
            f"{API_URL}order/{order_id}/offers/{offer_id}/reject",
            telegram_id
        )
        logger.info(
            f"Предложение {offer_id} для заказа {order_id} отклонено пользователем {telegram_id}: {updated_offer}")

        await callback.message.edit_text(
            f"Предложение ID {offer_id} по заказу ID {order_id} успешно отклонено!\n"
            f"Статус предложения: {updated_offer['status']}",
            reply_markup=None
        )
        await callback.answer("Предложение отклонено!")
    except Exception as e:
        logger.error(f"Ошибка при отклонении предложения: {e}")
        await callback.message.edit_text(
            f"Ошибка при отклонении предложения: {e}",
            reply_markup=None
        )
        await callback.answer("Ошибка!")