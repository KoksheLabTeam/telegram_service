from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.bot.config import API_URL
from app.bot.handlers.start import get_main_keyboard
from app.bot.handlers.utils import api_request, create_categories_keyboard, create_back_keyboard

router = Router()

class CreateOrderStates(StatesGroup):
    SELECT_CATEGORY = State()
    ENTER_TITLE = State()
    ENTER_DESCRIPTION = State()
    ENTER_PRICE = State()
    ENTER_DUE_DATE = State()
    CONFIRM = State()

@router.message(F.text == "Создать заказ")
async def start_create_order(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        categories = await api_request("GET", f"{API_URL}category/", telegram_id)
        await message.answer(
            "Выберите категорию:",
            reply_markup=create_categories_keyboard(categories)
        )
        await state.set_state(CreateOrderStates.SELECT_CATEGORY)
    except Exception as e:
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())

@router.callback_query(F.data.startswith("category_"))
async def select_category(callback: types.CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[1])
    await state.update_data(category_id=category_id)
    await callback.message.answer("Введите заголовок заказа:", reply_markup=create_back_keyboard())
    await state.set_state(CreateOrderStates.ENTER_TITLE)
    await callback.answer()

@router.message(CreateOrderStates.ENTER_TITLE)
async def enter_title(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    await state.update_data(title=message.text)
    await message.answer("Введите описание (или нажмите 'Пропустить'):", reply_markup=create_back_keyboard())
    await state.set_state(CreateOrderStates.ENTER_DESCRIPTION)

@router.message(CreateOrderStates.ENTER_DESCRIPTION)
async def enter_description(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    description = message.text if message.text != "Пропустить" else None
    await state.update_data(description=description)
    await message.answer("Введите желаемую цену:", reply_markup=create_back_keyboard())
    await state.set_state(CreateOrderStates.ENTER_PRICE)

@router.message(CreateOrderStates.ENTER_PRICE)
async def enter_price(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    try:
        price = float(message.text)
        await state.update_data(desired_price=price)
        await message.answer("Введите дату выполнения (гггг-мм-ддTчч:мм:сс):", reply_markup=create_back_keyboard())
        await state.set_state(CreateOrderStates.ENTER_DUE_DATE)
    except ValueError:
        await message.answer("Цена должна быть числом. Попробуйте снова:", reply_markup=create_back_keyboard())

@router.message(CreateOrderStates.ENTER_DUE_DATE)
async def enter_due_date(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    due_date = message.text
    await state.update_data(due_date=due_date)
    data = await state.get_data()
    await message.answer(
        f"Подтвердите заказ:\nКатегория: {data['category_id']}\nЗаголовок: {data['title']}\nОписание: {data.get('description', 'Нет')}\nЦена: {data['desired_price']}\nДата: {data['due_date']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_order")],
            [InlineKeyboardButton(text="Отмена", callback_data="cancel_order")]
        ])
    )
    await state.set_state(CreateOrderStates.CONFIRM)

@router.callback_query(F.data == "confirm_order")
async def confirm_order(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    data = await state.get_data()
    order_data = {
        "category_id": data["category_id"],
        "title": data["title"],
        "description": data.get("description"),
        "desired_price": data["desired_price"],
        "due_date": data["due_date"]
    }
    try:
        await api_request("POST", f"{API_URL}order/", telegram_id, json=order_data)
        await callback.message.answer("Заказ успешно создан!", reply_markup=get_main_keyboard())
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Создание заказа отменено.", reply_markup=get_main_keyboard())
    await state.clear()
    await callback.answer()