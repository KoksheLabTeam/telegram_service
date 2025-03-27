from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL
import logging

router = Router()
logger = logging.getLogger(__name__)

# Определяем состояния для создания, редактирования и удаления предложений
class OfferStates(StatesGroup):
    select_order = State()  # Выбор заказа для создания предложения
    price = State()         # Ввод цены для создания
    estimated_time = State()  # Ввод времени выполнения для создания
    select_offer_edit = State()  # Выбор предложения для редактирования
    price_edit = State()         # Ввод новой цены для редактирования
    estimated_time_edit = State()  # Ввод нового времени для редактирования
    select_offer_delete = State()  # Выбор предложения для удаления

# Главная точка входа для создания предложения
@router.message(F.text == "Создать предложение")
async def start_create_offer(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_executor"]:
        await message.answer(
            "Только исполнители могут создавать предложения.",
            reply_markup=get_main_keyboard(roles)
        )
        return

    try:
        user_profile = await api_request("GET", f"{API_URL}user/me", telegram_id)
        executor_categories = set(user_profile.get("category_ids", []))
        executor_city = user_profile.get("city_id")

        if not executor_categories or not executor_city:
            await message.answer(
                "Пожалуйста, обновите профиль, указав категории и город, чтобы видеть доступные заказы.",
                reply_markup=get_main_keyboard(roles)
            )
            return

        available_orders = await api_request("GET", f"{API_URL}order/available", telegram_id)
        filtered_orders = [
            order for order in available_orders
            if order["category_id"] in executor_categories and order["city_id"] == executor_city
        ]

        if not filtered_orders:
            await message.answer(
                "Нет доступных заказов в вашем городе и категориях.",
                reply_markup=get_main_keyboard(roles)
            )
            return

        orders_list = "\n\n".join([
            f"ID: {order['id']}\n"
            f"Название: {order['title']}\n"
            f"Описание: {order['description'] or 'Нет описания'}\n"
            f"Цена: {order['desired_price']} тенге\n"
            f"Дедлайн: {order['due_date']}"
            for order in filtered_orders
        ])
        await message.answer(
            f"Доступные заказы:\n{orders_list}\n\nВведите ID заказа, на который хотите подать предложение:",
            reply_markup=get_main_keyboard(roles)
        )
        await state.set_state(OfferStates.select_order)
    except Exception as e:
        logger.error(f"Ошибка при загрузке доступных заказов: {e}")
        await message.answer(
            f"Ошибка: {e}",
            reply_markup=get_main_keyboard(roles)
        )
        await state.clear()

# Обработка выбора заказа для создания предложения
@router.message(OfferStates.select_order)
async def process_order_selection(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        order_id = int(message.text.strip())
        available_orders = await api_request("GET", f"{API_URL}order/available", telegram_id)
        selected_order = next((order for order in available_orders if order["id"] == order_id), None)
        if not selected_order:
            await message.answer(
                "Заказ не найден или недоступен.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
            return

        await state.update_data(order_id=order_id)
        await message.answer("Введите вашу цену за выполнение заказа (в тенге):")
        await state.set_state(OfferStates.price)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
    except Exception as e:
        logger.error(f"Ошибка при выборе заказа: {e}")
        await message.answer(
            f"Ошибка: {e}",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()

# Обработка ввода цены для создания
@router.message(OfferStates.price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        if price <= 0:
            await message.answer("Цена должна быть больше 0.")
            return
        await state.update_data(price=price)
        await message.answer("Введите предполагаемое время выполнения (в часах):")
        await state.set_state(OfferStates.estimated_time)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для цены.")
    except Exception as e:
        logger.error(f"Ошибка при вводе цены: {e}")
        await message.answer(
            f"Ошибка: {e}",
            reply_markup=get_main_keyboard(await get_user_roles(message.from_user.id))
        )
        await state.clear()

# Обработка ввода времени и отправка предложения
@router.message(OfferStates.estimated_time)
async def process_estimated_time(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        estimated_time = int(message.text.strip())
        if estimated_time <= 0:
            await message.answer("Время выполнения должно быть больше 0.")
            return
        data = await state.get_data()
        offer_data = {
            "order_id": data["order_id"],
            "price": data["price"],
            "estimated_time": estimated_time
        }
        offer = await api_request("POST", f"{API_URL}offer/", telegram_id, data=offer_data)
        await message.answer(
            f"Предложение для заказа ID {offer['order_id']} успешно создано!\n"
            f"Цена: {offer['price']} тенге\n"
            f"Время выполнения: {offer['estimated_time']} часов",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для времени выполнения.")
    except Exception as e:
        logger.error(f"Ошибка при создании предложения: {e}")
        await message.answer(
            f"Ошибка: {e}",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()

# Команда "Мои предложения" для просмотра списка предложений
@router.message(F.text == "Мои предложения")
async def list_offers(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_executor"]:
        await message.answer(
            "Только исполнители могут просматривать свои предложения.",
            reply_markup=get_main_keyboard(roles)
        )
        return

    try:
        offers = await api_request("GET", f"{API_URL}offer/", telegram_id)
        if not offers:
            await message.answer(
                "У вас нет предложений.",
                reply_markup=get_main_keyboard(roles)
            )
            return

        offers_list = "\n\n".join([
            f"ID: {offer['id']}\n"
            f"Заказ ID: {offer['order_id']}\n"
            f"Цена: {offer['price']} тенге\n"
            f"Время выполнения: {offer['estimated_time']} часов\n"
            f"Статус: {offer['status']}"
            for offer in offers
        ])
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Редактировать", callback_data="edit_offer"),
             InlineKeyboardButton(text="Удалить", callback_data="delete_offer")]
        ])
        await message.answer(
            f"Ваши предложения:\n{offers_list}",
            reply_markup=inline_kb
        )
    except Exception as e:
        logger.error(f"Ошибка при загрузке предложений: {e}")
        await message.answer(
            f"Ошибка: {e}",
            reply_markup=get_main_keyboard(roles)
        )

# Обработка редактирования предложений
@router.callback_query(F.data == "edit_offer")
async def start_edit_offer(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    try:
        offers = await api_request("GET", f"{API_URL}offer/", telegram_id)
        editable_offers = [o for o in offers if o["status"] == "pending"]  # Только "pending" можно редактировать
        if not editable_offers:
            await callback.message.edit_text(
                "У вас нет предложений, доступных для редактирования.",
                reply_markup=None
            )
            await callback.answer()
            return

        offers_list = "\n".join([
            f"ID: {offer['id']} - Заказ ID: {offer['order_id']}"
            for offer in editable_offers
        ])
        await callback.message.edit_text(
            f"Выберите предложение для редактирования:\n{offers_list}\n\nВведите ID предложения:",
            reply_markup=None
        )
        await state.set_state(OfferStates.select_offer_edit)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при загрузке предложений для редактирования: {e}")
        await callback.message.edit_text(
            f"Ошибка: {e}",
            reply_markup=None
        )
        await state.clear()
        await callback.answer()

@router.message(OfferStates.select_offer_edit)
async def process_offer_edit_selection(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        offer_id = int(message.text.strip())
        offer = await api_request("GET", f"{API_URL}offer/{offer_id}", telegram_id)
        if offer["status"] != "pending":
            await message.answer(
                "Это предложение нельзя редактировать, так как оно уже принято или отклонено.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
            return

        await state.update_data(offer_id=offer_id)
        await message.answer(
            f"Текущая цена: {offer['price']} тенге\nВведите новую цену (в тенге):"
        )
        await state.set_state(OfferStates.price_edit)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID предложения.")
    except Exception as e:
        logger.error(f"Ошибка при выборе предложения для редактирования: {e}")
        await message.answer(
            f"Ошибка: {e}",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()

@router.message(OfferStates.price_edit)
async def process_price_edit(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        if price <= 0:
            await message.answer("Цена должна быть больше 0.")
            return
        await state.update_data(price=price)
        await message.answer("Введите новое предполагаемое время выполнения (в часах):")
        await state.set_state(OfferStates.estimated_time_edit)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для цены.")
    except Exception as e:
        logger.error(f"Ошибка при редактировании цены: {e}")
        await message.answer(
            f"Ошибка: {e}",
            reply_markup=get_main_keyboard(await get_user_roles(message.from_user.id))
        )
        await state.clear()

@router.message(OfferStates.estimated_time_edit)
async def process_estimated_time_edit(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        estimated_time = int(message.text.strip())
        if estimated_time <= 0:
            await message.answer("Время выполнения должно быть больше 0.")
            return
        data = await state.get_data()
        offer_data = {
            "price": data["price"],
            "estimated_time": estimated_time
        }
        updated_offer = await api_request(
            "PATCH",
            f"{API_URL}offer/{data['offer_id']}",
            telegram_id,
            data=offer_data
        )
        await message.answer(
            f"Предложение ID {updated_offer['id']} успешно обновлено!\n"
            f"Цена: {updated_offer['price']} тенге\n"
            f"Время выполнения: {updated_offer['estimated_time']} часов",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для времени выполнения.")
    except Exception as e:
        logger.error(f"Ошибка при обновлении предложения: {e}")
        await message.answer(
            f"Ошибка: {e}",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()

# Обработка удаления предложений
@router.callback_query(F.data == "delete_offer")
async def start_delete_offer(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    try:
        offers = await api_request("GET", f"{API_URL}offer/", telegram_id)
        deletable_offers = [o for o in offers if o["status"] == "pending"]  # Только "pending" можно удалять
        if not deletable_offers:
            await callback.message.edit_text(
                "У вас нет предложений, доступных для удаления.",
                reply_markup=None
            )
            await callback.answer()
            return

        offers_list = "\n".join([
            f"ID: {offer['id']} - Заказ ID: {offer['order_id']}"
            for offer in deletable_offers
        ])
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="cancel_delete")]
        ])
        await callback.message.edit_text(
            f"Выберите предложение для удаления:\n{offers_list}\n\nВведите ID предложения:",
            reply_markup=inline_kb
        )
        await state.set_state(OfferStates.select_offer_delete)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при загрузке предложений для удаления: {e}")
        await callback.message.edit_text(
            f"Ошибка: {e}",
            reply_markup=None
        )
        await state.clear()
        await callback.answer()

@router.message(OfferStates.select_offer_delete)
async def process_offer_delete_selection(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        offer_id = int(message.text.strip())
        offer = await api_request("GET", f"{API_URL}offer/{offer_id}", telegram_id)
        if offer["status"] != "pending":
            await message.answer(
                "Это предложение нельзя удалить, так как оно уже принято или отклонено.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
            return

        await api_request("DELETE", f"{API_URL}offer/{offer_id}", telegram_id)
        await message.answer(
            f"Предложение ID {offer_id} успешно удалено!",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID предложения.")
    except Exception as e:
        logger.error(f"Ошибка при удалении предложения: {e}")
        await message.answer(
            f"Ошибка: {e}",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()

@router.callback_query(F.data == "cancel_delete")
async def cancel_delete_offer(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Удаление предложения отменено.",
        reply_markup=None
    )
    await state.clear()
    await callback.answer()

# Просмотр списка доступных заказов (без изменений)
@router.message(F.text == "Список доступных заказов")
async def list_available_orders(message: Message):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_executor"]:
        await message.answer(
            "Только исполнители могут просматривать доступные заказы.",
            reply_markup=get_main_keyboard(roles)
        )
        return
    try:
        user_profile = await api_request("GET", f"{API_URL}user/me", telegram_id)
        logger.info(f"Профиль пользователя: {user_profile}")
        executor_categories = set(user_profile.get("category_ids", []))
        executor_city = user_profile.get("city_id")
        logger.info(f"Город исполнителя: {executor_city}")
        if not executor_categories or executor_city is None:
            await message.answer(
                "Пожалуйста, обновите профиль, указав категории и город.",
                reply_markup=get_main_keyboard(roles)
            )
            return
        available_orders = await api_request("GET", f"{API_URL}order/available", telegram_id)
        logger.info(f"Доступные заказы: {available_orders}")
        filtered_orders = [
            order for order in available_orders
            if order.get("category_id") in executor_categories and order.get("city_id") == executor_city
        ]
        if not filtered_orders:
            await message.answer(
                "Нет доступных заказов в вашем городе и категориях.",
                reply_markup=get_main_keyboard(roles)
            )
            return
        orders_list = "\n\n".join([
            f"ID: {order['id']}\n"
            f"Название: {order['title']}\n"
            f"Описание: {order['description'] or 'Нет описания'}\n"
            f"Цена: {order['desired_price']} тенге\n"
            f"Дедлайн: {order['due_date']}"
            for order in filtered_orders
        ])
        await message.answer(
            f"Доступные заказы:\n{orders_list}",
            reply_markup=get_main_keyboard(roles)
        )
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка доступных заказов: {e}")
        await message.answer(
            f"Ошибка: {e}",
            reply_markup=get_main_keyboard(roles)
        )