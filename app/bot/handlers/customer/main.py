from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL, BOT_TOKEN  # Предполагается, что BOT_TOKEN доступен в config
from app.core.models.order import OrderStatus  # Импортируем перечисление OrderStatus
import aiohttp
from datetime import datetime, timedelta
import logging
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

router = Router()
logger = logging.getLogger(__name__)

# Состояния для управления заказами
class OrderStates(StatesGroup):
    select_order_edit = State()  # Выбор заказа для редактирования
    edit_title = State()  # Ввод нового названия
    edit_description = State()  # Ввод нового описания
    edit_price = State()  # Ввод новой цены
    edit_due_date = State()  # Ввод нового дедлайна
    select_order_delete = State()  # Выбор заказа для удаления
    select_order_offers = State()  # Выбор заказа для просмотра предложений
    select_order_cancel = State()  # Выбор заказа для отмены
    select_order_review = State()  # Выбор заказа для отзыва
    input_rating = State()  # Ввод рейтинга для отзыва
    input_comment = State()  # Ввод комментария для отзыва
    offers_filter = State()  # Ввод фильтра для предложений
    offers_sort = State()  # Ввод сортировки для предложений
    chat_with_executor = State()  # Ввод сообщения для исполнителя

# Асинхронная функция для отправки сообщения через Telegram API
async def send_telegram_message(chat_id: int, text: str):
    async with aiohttp.ClientSession() as session:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                logger.error(f"Ошибка отправки сообщения в Telegram: {await response.text()}")
                return False
            return True

# Команда "Создать заказ"
@router.message(F.text == "Создать заказ")
async def start_create_order(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer("Только заказчики могут создавать заказы.", reply_markup=get_main_keyboard(roles))
        return
    try:
        cities = await api_request("GET", f"{API_URL}city/", telegram_id)
        categories = await api_request("GET", f"{API_URL}category/", telegram_id)
        if not cities or not categories:
            await message.answer("Нет доступных городов или категорий.", reply_markup=get_main_keyboard(roles))
            return
        city_list = "\n".join([f"{city['id']}: {city['name']}" for city in cities])
        category_list = "\n".join([f"{cat['id']}: {cat['name']}" for cat in categories])
        await message.answer(
            f"Доступные города:\n{city_list}\n\nДоступные категории:\n{category_list}\n\nВведите ID категории:"
        )
        await state.set_state(OrderStates.edit_title)
        await state.update_data(cities=cities, categories=categories, step="category")
    except Exception as e:
        logger.error(f"Ошибка при запуске создания заказа: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

@router.message(OrderStates.edit_title)
async def process_create_order(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    data = await state.get_data()
    step = data.get("step", "category")

    if step == "category":
        try:
            category_id = int(message.text.strip())
            if not any(cat["id"] == category_id for cat in data["categories"]):
                await message.answer("Неверный ID категории. Попробуйте снова:")
                return
            await state.update_data(category_id=category_id)
            await message.answer("Введите название заказа:")
            await state.update_data(step="title")
        except ValueError:
            await message.answer("Пожалуйста, введите корректный ID категории.")
    elif step == "title":
        await state.update_data(title=message.text.strip())
        await message.answer("Введите описание заказа (или /skip для пропуска):")
        await state.update_data(step="description")
    elif step == "description":
        if message.text.strip() != "/skip":
            await state.update_data(description=message.text.strip())
        await message.answer("Введите желаемую цену (в тенге):")
        await state.update_data(step="price")
    elif step == "price":
        try:
            price = float(message.text.strip())
            if price <= 0:
                await message.answer("Цена должна быть больше 0.")
                return
            await state.update_data(desired_price=price)
            await message.answer("Введите дедлайн (гггг-мм-дд чч:мм):")
            await state.update_data(step="due_date")
        except ValueError:
            await message.answer("Пожалуйста, введите корректное число для цены.")
    elif step == "due_date":
        try:
            due_date = datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
            if due_date < datetime.utcnow():
                await message.answer("Дедлайн не может быть в прошлом.")
                return
            data = await state.get_data()
            order_data = {
                "category_id": data["category_id"],
                "title": data["title"],
                "description": data.get("description"),
                "desired_price": data["desired_price"],
                "due_date": due_date.isoformat()
            }
            order = await api_request("POST", f"{API_URL}order/", telegram_id, data=order_data)
            await message.answer(
                f"Заказ успешно создан!\nID: {order['id']}\nНазвание: {order['title']}",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
        except ValueError:
            await message.answer("Пожалуйста, введите дату в формате гггг-мм-дд чч:мм.")
        except Exception as e:
            logger.error(f"Ошибка при создании заказа: {e}")
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
        editable_orders = [o for o in orders if o["status"] == OrderStatus.PENDING.value and o["customer_id"] == telegram_id]
        if not editable_orders:
            await message.answer("У вас нет заказов, доступных для редактирования.",
                                 reply_markup=get_main_keyboard(roles))
            return
        response = "Ваши заказы в ожидании:\n\n"
        for order in editable_orders:
            response += f"ID: {order['id']} - {order['title']}\n"
        await message.answer(response + "\nВведите ID заказа для редактирования:")
        await state.set_state(OrderStates.select_order_edit)
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов для редактирования: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

@router.message(OrderStates.select_order_edit)
async def process_edit_order_selection(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        order_id = int(message.text.strip())
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        order = next((o for o in orders if
                      o["id"] == order_id and o["status"] == OrderStatus.PENDING.value and o["customer_id"] == telegram_id), None)
        if not order:
            await message.answer("Заказ не найден или недоступен для редактирования.",
                                 reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
            await state.clear()
            return
        await state.update_data(order_id=order_id, current_order=order)
        await message.answer(f"Текущее название: {order['title']}\nВведите новое название (или /skip для пропуска):")
        await state.set_state(OrderStates.edit_title)
        await state.update_data(step="edit_title")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
    except Exception as e:
        logger.error(f"Ошибка при выборе заказа для редактирования: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

@router.message(OrderStates.edit_title, F.text.regexp(r"^(?!/skip).*$"))
async def process_edit_title(message: Message, state: FSMContext):
    data = await state.get_data()
    step = data.get("step")
    if step == "edit_title":
        await state.update_data(title=message.text.strip())
        await message.answer("Введите новое описание (или /skip для пропуска):")
        await state.update_data(step="edit_description")
        await state.set_state(OrderStates.edit_description)

@router.message(OrderStates.edit_description)
async def process_edit_description(message: Message, state: FSMContext):
    if message.text.strip() != "/skip":
        await state.update_data(description=message.text.strip())
    await message.answer("Введите новую желаемую цену (в тенге, или /skip для пропуска):")
    await state.set_state(OrderStates.edit_price)

@router.message(OrderStates.edit_price)
async def process_edit_price(message: Message, state: FSMContext):
    text = message.text.strip()
    if text != "/skip":
        try:
            price = float(text)
            if price <= 0:
                await message.answer("Цена должна быть больше 0.")
                return
            await state.update_data(desired_price=price)
        except ValueError:
            await message.answer("Пожалуйста, введите корректное число для цены.")
            return
    await message.answer("Введите новый дедлайн (гггг-мм-дд чч:мм, или /skip для пропуска):")
    await state.set_state(OrderStates.edit_due_date)

@router.message(OrderStates.edit_due_date)
async def process_edit_due_date(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    text = message.text.strip()
    data = await state.get_data()
    order_id = data["order_id"]
    update_data = {}
    if text != "/skip":
        try:
            due_date = datetime.strptime(text, "%Y-%m-%d %H:%M")
            if due_date < datetime.utcnow():
                await message.answer("Дедлайн не может быть в прошлом.")
                return
            update_data["due_date"] = due_date.isoformat()
        except ValueError:
            await message.answer("Пожалуйста, введите дату в формате гггг-мм-дд чч:мм.")
            return
    if "title" in data:
        update_data["title"] = data["title"]
    if "description" in data:
        update_data["description"] = data["description"]
    if "desired_price" in data:
        update_data["desired_price"] = data["desired_price"]

    if update_data:
        try:
            updated_order = await api_request("PATCH", f"{API_URL}order/{order_id}", telegram_id, data=update_data)
            await message.answer(
                f"Заказ ID {order_id} успешно обновлен!\n"
                f"Название: {updated_order['title']}\n"
                f"Описание: {updated_order['description'] or 'Нет'}\n"
                f"Цена: {updated_order['desired_price']} тенге\n"
                f"Дедлайн: {updated_order['due_date']}",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении заказа: {e}")
            await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
    else:
        await message.answer("Ничего не изменено.", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
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
        deletable_orders = [o for o in orders if o["status"] == OrderStatus.PENDING.value and o["customer_id"] == telegram_id]
        if not deletable_orders:
            await message.answer("У вас нет заказов, доступных для удаления.", reply_markup=get_main_keyboard(roles))
            return
        response = "Ваши заказы в ожидании:\n\n"
        for order in deletable_orders:
            response += f"ID: {order['id']} - {order['title']}\n"
        await message.answer(response + "\nВведите ID заказа для удаления:")
        await state.set_state(OrderStates.select_order_delete)
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов для удаления: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

@router.message(OrderStates.select_order_delete)
async def process_delete_order(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        order_id = int(message.text.strip())
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        order = next((o for o in orders if
                      o["id"] == order_id and o["status"] == OrderStatus.PENDING.value and o["customer_id"] == telegram_id), None)
        if not order:
            await message.answer("Заказ не найден или недоступен для удаления.",
                                 reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
            await state.clear()
            return
        await api_request("DELETE", f"{API_URL}order/{order_id}", telegram_id)
        await message.answer(f"Заказ ID {order_id} успешно удален!",
                             reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
    except Exception as e:
        logger.error(f"Ошибка при удалении заказа: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

# Просмотр предложений
@router.message(F.text == "Посмотреть предложения")
async def start_view_offers(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer("Только заказчики могут просматривать предложения.", reply_markup=get_main_keyboard(roles))
        return
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        pending_orders = [o for o in orders if o["status"] == OrderStatus.PENDING.value and o["customer_id"] == telegram_id]
        if not pending_orders:
            await message.answer("У вас нет заказов в ожидании с предложениями.", reply_markup=get_main_keyboard(roles))
            return
        response = "Ваши заказы в ожидании:\n\n"
        for order in pending_orders:
            response += f"ID: {order['id']} - {order['title']}\n"
        await message.answer(response + "\nВведите ID заказа для просмотра предложений:")
        await state.set_state(OrderStates.select_order_offers)
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов для просмотра предложений: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

@router.message(OrderStates.select_order_offers)
async def process_select_order_offers(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        order_id = int(message.text.strip())
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        order = next((o for o in orders if
                      o["id"] == order_id and o["status"] == OrderStatus.PENDING.value and o["customer_id"] == telegram_id), None)
        if not order:
            await message.answer("Заказ не найден или недоступен.",
                                 reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
            await state.clear()
            return
        await state.update_data(order_id=order_id)
        await message.answer(
            "Выберите фильтр для предложений:\n"
            "1. Все\n"
            "2. Только pending\n"
            "3. Только accepted\n"
            "4. Только rejected\n"
            "Введите номер (или /skip для всех):"
        )
        await state.set_state(OrderStates.offers_filter)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
    except Exception as e:
        logger.error(f"Ошибка при выборе заказа для предложений: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

@router.message(OrderStates.offers_filter)
async def process_offers_filter(message: Message, state: FSMContext):
    text = message.text.strip()
    filter_map = {"1": None, "2": "pending", "3": "accepted", "4": "rejected"}
    if text == "/skip":
        await state.update_data(filter_status=None)
    elif text in filter_map:
        await state.update_data(filter_status=filter_map[text])
    else:
        await message.answer("Пожалуйста, выберите корректный номер фильтра (1-4) или /skip.")
        return
    await message.answer(
        "Выберите сортировку:\n"
        "1. Без сортировки\n"
        "2. По цене (возрастание)\n"
        "3. По рейтингу исполнителя (убывание)\n"
        "Введите номер (или /skip для без сортировки):"
    )
    await state.set_state(OrderStates.offers_sort)

@router.message(OrderStates.offers_sort)
async def process_offers_sort(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    text = message.text.strip()
    sort_map = {"1": None, "2": "price", "3": "executor_rating"}
    if text == "/skip":
        await state.update_data(sort_by=None)
    elif text in sort_map:
        await state.update_data(sort_by=sort_map[text])
    else:
        await message.answer("Пожалуйста, выберите корректный номер сортировки (1-3) или /skip.")
        return

    data = await state.get_data()
    order_id = data["order_id"]
    filter_status = data.get("filter_status")
    sort_by = data.get("sort_by")

    try:
        url = f"{API_URL}order/{order_id}/offers"
        params = {}
        if filter_status:
            params["status"] = filter_status
        if sort_by:
            params["sort_by"] = sort_by
        offers = await api_request("GET", url, telegram_id, params=params if params else None)

        if not offers:
            await message.answer(f"По заказу ID {order_id} нет предложений с выбранными фильтрами.",
                                 reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
            await state.clear()
            return

        response = f"Предложения по заказу ID {order_id}:\n\n"
        inline_buttons = []
        for offer in offers:
            response += (
                f"ID: {offer['id']}\n"
                f"Исполнитель: {offer['executor_id']} (Рейтинг: {offer['executor_rating']})\n"
                f"Цена: {offer['price']} тенге\n"
                f"Время: {offer['estimated_time']} часов\n"
                f"Статус: {offer['status']}\n\n"
            )
            buttons = []
            if offer["status"] == "pending":
                buttons.extend([
                    InlineKeyboardButton(text=f"Принять {offer['id']}",
                                         callback_data=f"accept_offer_{order_id}_{offer['id']}"),
                    InlineKeyboardButton(text=f"Отклонить {offer['id']}",
                                         callback_data=f"reject_offer_{order_id}_{offer['id']}")
                ])
            buttons.extend([
                InlineKeyboardButton(text=f"Подробнее об исполнителе {offer['executor_id']}",
                                     callback_data=f"executor_info_{offer['executor_id']}"),
                InlineKeyboardButton(text=f"Связаться с исполнителем {offer['executor_id']}",
                                     callback_data=f"chat_executor_{order_id}_{offer['executor_id']}")
            ])
            inline_buttons.append(buttons)

        inline_kb = InlineKeyboardMarkup(inline_keyboard=inline_buttons)
        await message.answer(response, reply_markup=inline_kb)
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при просмотре предложений: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

@router.callback_query(lambda c: c.data.startswith("accept_offer_"))
async def process_accept_offer(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    _, order_id, offer_id = callback.data.split("_")
    try:
        order = await api_request("GET", f"{API_URL}order/{order_id}", telegram_id)
        if order["customer_id"] != telegram_id:
            await callback.message.edit_text("Вы не можете принять предложение для этого заказа.")
            await callback.answer()
            return
        updated_order = await api_request("POST", f"{API_URL}offer/{order_id}/offers/{offer_id}/accept", telegram_id)
        await callback.message.edit_text(
            f"Предложение ID {offer_id} принято! Заказ ID {order_id} теперь в статусе 'В процессе'.",
            reply_markup=None
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при принятии предложения: {e}")
        await callback.message.edit_text(f"Ошибка: {e}", reply_markup=None)
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("reject_offer_"))
async def process_reject_offer(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    _, order_id, offer_id = callback.data.split("_")
    try:
        order = await api_request("GET", f"{API_URL}order/{order_id}", telegram_id)
        if order["customer_id"] != telegram_id:
            await callback.message.edit_text("Вы не можете отклонить предложение для этого заказа.")
            await callback.answer()
            return
        updated_offer = await api_request("POST", f"{API_URL}offer/{order_id}/offers/{offer_id}/reject", telegram_id)
        await callback.message.edit_text(
            f"Предложение ID {offer_id} отклонено!",
            reply_markup=None
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при отклонении предложения: {e}")
        await callback.message.edit_text(f"Ошибка: {e}", reply_markup=None)
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("executor_info_"))
async def process_executor_info(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    _, executor_id = callback.data.split("_")
    try:
        executor = await api_request("GET", f"{API_URL}user/{executor_id}", telegram_id)
        response = (
            f"Информация об исполнителе ID {executor_id}:\n"
            f"Имя: {executor.get('name', 'Не указано')}\n"
            f"Рейтинг: {executor.get('rating', 'Нет рейтинга')}\n"
            f"Город: {executor.get('city_id', 'Не указан')}\n"
            f"Категории: {', '.join(str(cat) for cat in executor.get('category_ids', [])) or 'Не указаны'}\n"
        )
        await callback.message.answer(response)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при запросе информации об исполнителе: {e}")
        await callback.message.answer(f"Ошибка: {e}")
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("chat_executor_"))
async def start_chat_with_executor(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    _, order_id, executor_id = callback.data.split("_")
    try:
        order = await api_request("GET", f"{API_URL}order/{order_id}", telegram_id)
        if order["customer_id"] != telegram_id:
            await callback.message.edit_text("Вы не можете связаться с исполнителем для этого заказа.")
            await callback.answer()
            return
        await state.update_data(order_id=order_id, executor_id=executor_id)
        await callback.message.answer("Введите сообщение для исполнителя:")
        await state.set_state(OrderStates.chat_with_executor)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при запуске чата с исполнителем: {e}")
        await callback.message.edit_text(f"Ошибка: {e}", reply_markup=None)
        await callback.answer()

@router.message(OrderStates.chat_with_executor)
async def process_chat_message(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    data = await state.get_data()
    order_id = data["order_id"]
    executor_id = data["executor_id"]

    try:
        executor = await api_request("GET", f"{API_URL}user/{executor_id}", telegram_id)
        executor_telegram_id = executor.get("telegram_id")
        if not executor_telegram_id:
            await message.answer("У исполнителя не указан Telegram ID.",
                                 reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
            await state.clear()
            return

        customer = await api_request("GET", f"{API_URL}user/me", telegram_id)
        customer_name = customer.get("name", "Заказчик")
        message_text = f"Сообщение от {customer_name} (Заказ ID {order_id}):\n{message.text.strip()}"

        success = await send_telegram_message(executor_telegram_id, message_text)
        if success:
            await message.answer(
                f"Сообщение успешно отправлено исполнителю ID {executor_id}!",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
        else:
            await message.answer(
                "Не удалось отправить сообщение исполнителю.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения исполнителю: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

# Список заказов
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
        status_display = {
            OrderStatus.PENDING.value: "Ожидает",
            OrderStatus.IN_PROGRESS.value: "В процессе",
            OrderStatus.COMPLETED.value: "Завершён",
            OrderStatus.CANCELED.value: "Отменён"
        }
        for order in orders:
            status = status_display.get(order["status"], order["status"])
            response += f"ID: {order['id']} - {order['title']} ({status})\n"
        await message.answer(response, reply_markup=get_main_keyboard(roles))
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

# Отмена заказа
@router.message(F.text == "Отменить заказ")
async def cancel_order_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer("Только заказчики могут отменять заказы.", reply_markup=get_main_keyboard(roles))
        return
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        cancellable_orders = [
            o for o in orders
            if o["status"] == OrderStatus.PENDING.value and o["customer_id"] == telegram_id and
               (datetime.utcnow() - datetime.fromisoformat(o["created_at"].replace("Z", "+00:00"))) < timedelta(minutes=5)
        ]
        if not cancellable_orders:
            await message.answer("У вас нет заказов, доступных для отмены.", reply_markup=get_main_keyboard(roles))
            return
        response = "Ваши заказы, доступные для отмены:\n\n"
        for order in cancellable_orders:
            response += f"ID: {order['id']} - {order['title']}\n"
        await message.answer(response + "\nВведите ID заказа для отмены:")
        await state.set_state(OrderStates.select_order_cancel)
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов для отмены: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

@router.message(OrderStates.select_order_cancel)
async def process_cancel_order(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        order_id = int(message.text.strip())
        canceled_order = await api_request("POST", f"{API_URL}order/{order_id}/cancel", telegram_id)
        await message.answer(f"Заказ ID {order_id} успешно отменен!",
                             reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
    except Exception as e:
        logger.error(f"Ошибка при отмене заказа: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

# Оставить отзыв
@router.message(F.text == "Оставить отзыв")
async def start_review(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer("Только заказчики могут оставлять отзывы.", reply_markup=get_main_keyboard(roles))
        return
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        completed_orders = [o for o in orders if o["status"] == OrderStatus.COMPLETED.value and o["customer_id"] == telegram_id]
        if not completed_orders:
            await message.answer("У вас нет завершенных заказов для отзыва.", reply_markup=get_main_keyboard(roles))
            return
        response = "Ваши завершенные заказы:\n\n"
        for order in completed_orders:
            response += f"ID: {order['id']} - {order['title']}\n"
        await message.answer(response + "\nВведите ID заказа для отзыва:")
        await state.set_state(OrderStates.select_order_review)
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов для отзыва: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(roles))

@router.message(OrderStates.select_order_review)
async def process_review_order_selection(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        order_id = int(message.text.strip())
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        order = next((o for o in orders if
                      o["id"] == order_id and o["status"] == OrderStatus.COMPLETED.value and o["customer_id"] == telegram_id), None)
        if not order:
            await message.answer("Заказ не найден или не завершен.",
                                 reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
            await state.clear()
            return
        await state.update_data(order_id=order_id, executor_id=order["executor_id"])
        await message.answer("Введите рейтинг (от 1 до 5):")
        await state.set_state(OrderStates.input_rating)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
    except Exception as e:
        logger.error(f"Ошибка при выборе заказа для отзыва: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

@router.message(OrderStates.input_rating)
async def process_review_rating(message: Message, state: FSMContext):
    try:
        rating = int(message.text.strip())
        if not 1 <= rating <= 5:
            await message.answer("Рейтинг должен быть от 1 до 5.")
            return
        await state.update_data(rating=rating)
        await message.answer("Введите комментарий (или /skip для пропуска):")
        await state.set_state(OrderStates.input_comment)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для рейтинга.")
    except Exception as e:
        logger.error(f"Ошибка при вводе рейтинга: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(message.from_user.id)))
        await state.clear()

@router.message(OrderStates.input_comment)
async def process_review_comment(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    data = await state.get_data()
    comment = message.text.strip() if message.text.strip() != "/skip" else None
    review_data = {
        "order_id": data["order_id"],
        "target_id": data["executor_id"],
        "rating": data["rating"],
        "comment": comment
    }
    try:
        review = await api_request("POST", f"{API_URL}review/", telegram_id, data=review_data)
        await message.answer(
            f"Отзыв успешно оставлен!\nРейтинг: {review['rating']}\nКомментарий: {review['comment'] or 'Нет'}",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при создании отзыва: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()