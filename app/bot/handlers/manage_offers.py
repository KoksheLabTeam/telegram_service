from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.core.services.order import get_orders_by_user, update_order_by_id
from app.core.services.offer import get_offer_by_id, update_offer_by_id
from app.core.schemas.order import OrderUpdate
from app.core.schemas.offer import OfferUpdate
from app.core.models.user import User
from app.bot.config import ADMIN_TELEGRAM_ID
from app.bot.handlers.utils import get_db_session, get_user_telegram_id
from .start import get_main_keyboard

router = Router()

class ManageOffers(StatesGroup):
    select_order = State()

@router.message(F.text == "Посмотреть предложения")
async def start_manage_offers(message: Message, state: FSMContext):
    telegram_id = get_user_telegram_id(message)
    session = next(get_db_session())
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user or not user.is_customer:
            roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": user.is_executor if user else False, "is_customer": user.is_customer if user else False}
            await message.answer("Только заказчики могут просматривать предложения.", reply_markup=get_main_keyboard(roles))
            return
        orders = get_orders_by_user(session, telegram_id)
        if not orders:
            roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": user.is_executor, "is_customer": user.is_customer}
            await message.answer("У вас нет заказов.", reply_markup=get_main_keyboard(roles))
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"ID {order.id} - {order.title}", callback_data=f"view_offers_{order.id}")]
            for order in orders
        ] + [[InlineKeyboardButton(text="Отмена", callback_data="cancel")]])
        await message.answer("Выберите заказ для просмотра предложений:", reply_markup=keyboard)
        await state.set_state(ManageOffers.select_order)
    except Exception as e:
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())

@router.callback_query(ManageOffers.select_order, F.data.startswith("view_offers_"))
async def show_offers(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    telegram_id = callback.from_user.id
    session = next(get_db_session())
    try:
        order = session.query(Order).filter(Order.id == order_id, Order.customer_id == telegram_id).first()
        if not order:
            await callback.message.answer("Заказ не найден или не принадлежит вам.", reply_markup=get_main_keyboard({"is_customer": True}))
            await state.clear()
            await callback.answer()
            return
        offers = order.offers
        if not offers:
            await callback.message.answer("По этому заказу нет предложений.", reply_markup=get_main_keyboard({"is_customer": True}))
            await state.clear()
            await callback.answer()
            return
        response = f"Предложения по заказу ID {order_id}:\n\n"
        keyboard_buttons = []
        for offer in offers:
            executor = offer.executor
            start_date = offer.start_date.strftime("%Y-%m-%d") if offer.start_date else "Не указано"
            response += (
                f"ID предложения: {offer.id}\n"
                f"Исполнитель: {executor.name} (Рейтинг: {executor.rating})\n"
                f"Цена: {offer.price} тенге\n"
                f"Время: {offer.estimated_time} часов\n"
                f"Дата начала: {start_date}\n"
                f"Статус: {offer.status}\n\n"
            )
            if offer.status == "pending":
                keyboard_buttons.append([
                    InlineKeyboardButton(text=f"Принять {offer.id}", callback_data=f"accept_offer_{offer.id}_{order_id}"),
                    InlineKeyboardButton(text=f"Отклонить {offer.id}", callback_data=f"reject_offer_{offer.id}_{order_id}")
                ])
        keyboard_buttons.append([InlineKeyboardButton(text="Назад", callback_data="cancel")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.answer(response.strip(), reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer(f"Ошибка загрузки предложений: {e}", reply_markup=get_main_keyboard({"is_customer": True}))
        await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("accept_offer_"))
async def accept_offer(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    offer_id, order_id = map(int, callback.data.split("_")[2:4])
    session = next(get_db_session())
    try:
        offer = get_offer_by_id(session, offer_id)
        if offer.order_id != order_id or offer.status != "pending":
            await callback.message.answer("Предложение недоступно для принятия.", reply_markup=get_main_keyboard({"is_customer": True}))
            return
        order_update = OrderUpdate(executor_id=offer.executor_id, status="В_прогрессе")
        update_order_by_id(session, order_update, order_id)
        offer_update = OfferUpdate(status="accepted")
        update_offer_by_id(session, offer_update, offer_id)
        executor = offer.executor
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": True}
        await callback.message.answer(
            f"Предложение принято, исполнитель назначен!\nСвяжитесь с исполнителем: @{executor.username}",
            reply_markup=get_main_keyboard(roles)
        )
        await state.clear()
    except Exception as e:
        await callback.message.answer(f"Ошибка принятия предложения: {e}", reply_markup=get_main_keyboard({"is_customer": True}))
        await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("reject_offer_"))
async def reject_offer(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    offer_id, order_id = map(int, callback.data.split("_")[2:4])
    session = next(get_db_session())
    try:
        offer = get_offer_by_id(session, offer_id)
        if offer.order_id != order_id or offer.status != "pending":
            await callback.message.answer("Предложение недоступно для отклонения.", reply_markup=get_main_keyboard({"is_customer": True}))
            return
        offer_update = OfferUpdate(status="rejected")
        update_offer_by_id(session, offer_update, offer_id)
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": True}
        await callback.message.answer("Предложение отклонено.", reply_markup=get_main_keyboard(roles))
        await state.clear()
    except Exception as e:
        await callback.message.answer(f"Ошибка отклонения предложения: {e}", reply_markup=get_main_keyboard({"is_customer": True}))
        await state.clear()
    await callback.answer()

@router.callback_query(ManageOffers.select_order, F.data == "cancel")
async def cancel_manage_offers(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    session = next(get_db_session())
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": user.is_executor if user else False, "is_customer": user.is_customer if user else True}
    except Exception:
        roles = {"is_admin": telegram_id == ADMIN_TELEGRAM_ID, "is_executor": False, "is_customer": True}
    await state.clear()
    await callback.message.answer("Действие отменено.", reply_markup=get_main_keyboard(roles))
    await callback.answer()