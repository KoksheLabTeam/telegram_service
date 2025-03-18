from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL
import logging

router = Router()
logger = logging.getLogger(__name__)

# Определяем состояния для редактирования заказа
class EditOrderStates(StatesGroup):
    select_order = State()
    title = State()
    description = State()
    price = State()
    deadline = State()

# Определяем состояния для отмены и удаления заказа
class CancelOrderStates(StatesGroup):
    select_order = State()

class DeleteOrderStates(StatesGroup):
    select_order = State()

# Главная точка входа для заказчиков
@router.message(F.text == "Список заказов")
async def list_orders(message: Message):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer("Только заказчики могут просматривать свои заказы.", reply_markup=get_main_keyboard(roles))
        return
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        if not orders:
            await message.answer("У вас нет заказов.", reply_markup=get_main_keyboard(roles))
            return
        orders_list = "\n\n".join([
            f"ID: {order['id']}\n"
            f"Название: {order['title']}\n"
            f"Описание: {order['description']}\n"
            f"Цена: {order['price']} тенге\n"
            f"Дедлайн: {order['deadline']}\n"
            f"Статус: {order['status']}"
            for order in orders
        ])
        await message.answer(f"Ваши заказы:\n{orders_list}", reply_markup=get_main_keyboard(roles))
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка заказов: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

# Отмена заказа
@router.message(F.text == "Отменить заказ")
async def start_cancel_order(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer("Только заказчики могут отменять заказы.", reply_markup=get_main_keyboard(roles))
        return
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        cancellable_orders = [o for o in orders if o["status"] == "В_ожидании"]
        if not cancellable_orders:
            await message.answer("Нет заказов, доступных для отмены.", reply_markup=get_main_keyboard(roles))
            await state.clear()
            return
        orders_list = "\n".join([f"ID: {o['id']} - {o['title']}" for o in cancellable_orders])
        await message.answer(
            f"Выберите заказ для отмены (доступно в течение 5 минут после создания):\n{orders_list}\n\nВведите ID заказа:",
            reply_markup=get_main_keyboard(roles)
        )
        await state.set_state(CancelOrderStates.select_order)
    except Exception as e:
        logger.error(f"Ошибка при загрузке заказов для отмены: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))
        await state.clear()

@router.message(CancelOrderStates.select_order)
async def process_cancel_order(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        order_id = int(message.text.strip())
        order = await api_request("POST", f"{API_URL}order/{order_id}/cancel", telegram_id)
        await message.answer(
            f"Заказ ID {order['id']} успешно отменён!",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
    except Exception as e:
        logger.error(f"Ошибка при отмене заказа: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

# Редактирование заказа
@router.message(F.text == "Редактировать заказ")
async def start_edit_order(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer("Только заказчики могут редактировать заказы.", reply_markup=get_main_keyboard(roles))
        return
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        editable_orders = [o for o in orders if o["status"] == "В_ожидании"]
        if not editable_orders:
            await message.answer("Нет заказов, доступных для редактирования.", reply_markup=get_main_keyboard(roles))
            await state.clear()
            return
        orders_list = "\n".join([f"ID: {o['id']} - {o['title']}" for o in editable_orders])
        await message.answer(
            f"Выберите заказ для редактирования:\n{orders_list}\n\nВведите ID заказа:",
            reply_markup=get_main_keyboard(roles)
        )
        await state.set_state(EditOrderStates.select_order)
    except Exception as e:
        logger.error(f"Ошибка при загрузке заказов для редактирования: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))
        await state.clear()

@router.message(EditOrderStates.select_order)
async def process_edit_order_selection(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        order_id = int(message.text.strip())
        order = await api_request("GET", f"{API_URL}order/{order_id}", telegram_id)
        if order["status"] != "В_ожидании" or order["customer_id"] != telegram_id:
            await message.answer(
                "Этот заказ нельзя редактировать.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
            return
        await state.update_data(order_id=order_id)
        await message.answer(
            f"Текущее название: {order['title']}\nВведите новое название (или отправьте текущее для пропуска):"
        )
        await state.set_state(EditOrderStates.title)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
    except Exception as e:
        logger.error(f"Ошибка при выборе заказа для редактирования: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

@router.message(EditOrderStates.title)
async def process_edit_title(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(title=title)
    await message.answer("Введите новое описание (или отправьте текущее для пропуска):")
    await state.set_state(EditOrderStates.description)

@router.message(EditOrderStates.description)
async def process_edit_description(message: Message, state: FSMContext):
    description = message.text.strip()
    await state.update_data(description=description)
    await message.answer("Введите новую цену в тенге (или отправьте текущую для пропуска):")
    await state.set_state(EditOrderStates.price)

@router.message(EditOrderStates.price)
async def process_edit_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        if price <= 0:
            await message.answer("Цена должна быть больше 0.")
            return
        await state.update_data(price=price)
        await message.answer("Введите новый дедлайн (формат: ГГГГ-ММ-ДД ЧЧ:ММ, например, 2025-12-31 23:59):")
        await state.set_state(EditOrderStates.deadline)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для цены.")
    except Exception as e:
        logger.error(f"Ошибка при вводе цены: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(message.from_user.id)))
        await state.clear()

@router.message(EditOrderStates.deadline)
async def process_edit_deadline(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        deadline = message.text.strip()
        # Простая проверка формата, API сам валидирует ISO формат
        if len(deadline.split()) != 2 or len(deadline.split()[0].split('-')) != 3:
            await message.answer("Пожалуйста, используйте формат ГГГГ-ММ-ДД ЧЧ:ММ.")
            return
        data = await state.get_data()
        order_data = {
            "title": data["title"],
            "description": data["description"],
            "price": data["price"],
            "deadline": deadline
        }
        order = await api_request("PATCH", f"{API_URL}order/{data['order_id']}", telegram_id, data=order_data)
        await message.answer(
            f"Заказ ID {order['id']} успешно обновлён!\n"
            f"Название: {order['title']}\n"
            f"Описание: {order['description']}\n"
            f"Цена: {order['price']} тенге\n"
            f"Дедлайн: {order['deadline']}",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при редактировании заказа: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

# Удаление заказа
@router.message(F.text == "Удалить заказ")
async def start_delete_order(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer("Только заказчики могут удалять заказы.", reply_markup=get_main_keyboard(roles))
        return
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        deletable_orders = [o for o in orders if o["status"] == "В_ожидании"]
        if not deletable_orders:
            await message.answer("Нет заказов, доступных для удаления.", reply_markup=get_main_keyboard(roles))
            await state.clear()
            return
        orders_list = "\n".join([f"ID: {o['id']} - {o['title']}" for o in deletable_orders])
        await message.answer(
            f"Выберите заказ для удаления:\n{orders_list}\n\nВведите ID заказа:",
            reply_markup=get_main_keyboard(roles)
        )
        await state.set_state(DeleteOrderStates.select_order)
    except Exception as e:
        logger.error(f"Ошибка при загрузке заказов для удаления: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))
        await state.clear()

@router.message(DeleteOrderStates.select_order)
async def process_delete_order(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        order_id = int(message.text.strip())
        await api_request("DELETE", f"{API_URL}order/{order_id}", telegram_id)
        await message.answer(
            f"Заказ ID {order_id} успешно удалён!",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
    except Exception as e:
        logger.error(f"Ошибка при удалении заказа: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

@router.message(F.text == "Редактировать отзыв")
async def edit_review_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer("Только заказчики могут редактировать отзывы.", reply_markup=get_main_keyboard(roles))
        return
    reviews = await api_request("GET", f"{API_URL}review/", telegram_id)
    if not reviews:
        await message.answer("У вас нет отзывов.", reply_markup=get_main_keyboard(roles))
        return
    response = "Ваши отзывы:\n" + "\n".join([f"ID: {r['id']} - Заказ ID: {r['order_id']}" for r in reviews])
    await message.answer(response + "\nВведите ID отзыва:")
    await state.set_state(EditReviewStates.select_review)
