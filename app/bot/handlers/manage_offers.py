from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.utils import api_request, get_user_telegram_id
from app.bot.config import ADMIN_TELEGRAM_ID, API_URL

router = Router()

def get_main_keyboard(roles: dict = None):
    from .start import get_main_keyboard
    return get_main_keyboard(roles)

class ManageOffers(StatesGroup):
    select_order = State()

@router.message(F.text == "Посмотреть предложения")
async def start_manage_offers(message: Message, state: FSMContext):
    telegram_id = get_user_telegram_id(message)
    try:
        user = await api_request("GET", f"{API_URL}user/me", telegram_id)
        if not user["is_customer"]:
            roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": user["is_executor"], "is_customer": user["is_customer"]}
            await message.answer("Только заказчики могут просматривать предложения.", reply_markup=get_main_keyboard(roles))
            return
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        if not orders:
            roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": user["is_executor"], "is_customer": user["is_customer"]}
            await message.answer("У вас нет заказов.", reply_markup=get_main_keyboard(roles))
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"ID {order['id']} - {order['title']}", callback_data=f"view_offers_{order['id']}")]
            for order in orders
        ] + [[InlineKeyboardButton(text="Отмена", callback_data="cancel")]])
        await message.answer("Выберите заказ для просмотра предложений:", reply_markup=keyboard)
        await state.set_state(ManageOffers.select_order)
    except Exception as e:
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": False}
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

@router.callback_query(ManageOffers.select_order, F.data.startswith("view_offers_"))
async def show_offers(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    telegram_id = callback.from_user.id
    try:
        offers = await api_request("GET", f"{API_URL}order/{order_id}/offers", telegram_id)
        if not offers:
            roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": True}
            await callback.message.answer("По этому заказу нет предложений.", reply_markup=get_main_keyboard(roles))
            await state.clear()
            await callback.answer()
            return

        response = f"Предложения по заказу ID {order_id}:\n\n"
        keyboard_buttons = []
        for offer in offers:
            executor = await api_request("GET", f"{API_URL}user/{offer['executor_id']}", telegram_id)
            start_date = offer.get("start_date", "Не указано").split("T")[0] if offer.get("start_date") else "Не указано"
            response += (
                f"ID предложения: {offer['id']}\n"
                f"Исполнитель: {executor['name']} (Рейтинг: {executor['rating']})\n"
                f"Цена: {offer['price']} тенге\n"
                f"Время: {offer['estimated_time']} часов\n"
                f"Дата начала: {start_date}\n"
                f"Статус: {offer['status']}\n\n"
            )
            if offer["status"] == "pending":
                keyboard_buttons.append([
                    InlineKeyboardButton(text=f"Принять {offer['id']}", callback_data=f"accept_offer_{offer['id']}_{order_id}"),
                    InlineKeyboardButton(text=f"Отклонить {offer['id']}", callback_data=f"reject_offer_{offer['id']}_{order_id}")
                ])
        keyboard_buttons.append([InlineKeyboardButton(text="Назад", callback_data="cancel")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.answer(response.strip(), reply_markup=keyboard)
    except Exception as e:
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": True}
        await callback.message.answer(f"Ошибка загрузки предложений: {e}", reply_markup=get_main_keyboard(roles))
        await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("accept_offer_"))
async def accept_offer(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    offer_id, order_id = map(int, callback.data.split("_")[2:4])
    try:
        order = await api_request("POST", f"{API_URL}order/{order_id}/offers/{offer_id}/accept", telegram_id)
        executor = await api_request("GET", f"{API_URL}user/{order['executor_id']}", telegram_id)
        user = await api_request("GET", f"{API_URL}user/me", telegram_id)
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": user["is_executor"], "is_customer": user["is_customer"]}
        await callback.message.answer(
            f"Предложение принято, исполнитель назначен!\nСвяжитесь с исполнителем: @{executor['username']}",
            reply_markup=get_main_keyboard(roles)
        )
        await state.clear()
    except Exception as e:
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": True}
        await callback.message.answer(f"Ошибка принятия предложения: {e}", reply_markup=get_main_keyboard(roles))
        await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("reject_offer_"))
async def reject_offer(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    offer_id, order_id = map(int, callback.data.split("_")[2:4])
    try:
        await api_request("POST", f"{API_URL}order/{order_id}/offers/{offer_id}/reject", telegram_id)
        user = await api_request("GET", f"{API_URL}user/me", telegram_id)
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": user["is_executor"], "is_customer": user["is_customer"]}
        await callback.message.answer("Предложение отклонено.", reply_markup=get_main_keyboard(roles))
        await state.clear()
    except Exception as e:
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": True}
        await callback.message.answer(f"Ошибка отклонения предложения: {e}", reply_markup=get_main_keyboard(roles))
        await state.clear()
    await callback.answer()

@router.callback_query(ManageOffers.select_order, F.data == "cancel")
async def cancel_manage_offers(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    try:
        user = await api_request("GET", f"{API_URL}user/me", telegram_id)
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": user["is_executor"], "is_customer": user["is_customer"]}
    except Exception:
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": False}
    await state.clear()
    await callback.message.answer("Действие отменено.", reply_markup=get_main_keyboard(roles))
    await callback.answer()