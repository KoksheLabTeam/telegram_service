from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bot.handlers.common import api_request, get_main_keyboard, get_user_roles
from app.bot.config import API_URL
import logging

router = Router()
logger = logging.getLogger(__name__)

# Определяем состояния для управления отзывами
class ReviewStates(StatesGroup):
    select_action = State()  # Выбор действия (создать, просмотреть, редактировать)
    select_order_create = State()  # Выбор заказа для создания отзыва
    rating_create = State()  # Ввод рейтинга для создания отзыва
    comment_create = State()  # Ввод комментария для создания отзыва
    select_review_view = State()  # Выбор отзыва для просмотра
    select_review_edit = State()  # Выбор отзыва для редактирования
    rating_edit = State()  # Ввод нового рейтинга для редактирования
    comment_edit = State()  # Ввод нового комментария для редактирования

# Главная точка входа для отзывов
@router.message(F.text == "Оставить отзыв")
async def review_menu(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    roles = await get_user_roles(telegram_id)
    if not roles["is_customer"]:
        await message.answer("Только заказчики могут работать с отзывами.", reply_markup=get_main_keyboard(roles))
        return
    await message.answer(
        "Выберите действие с отзывами:\n1. Оставить новый отзыв\n2. Посмотреть мои отзывы\n3. Редактировать отзыв",
        reply_markup=get_main_keyboard(roles)
    )
    await state.set_state(ReviewStates.select_action)

# Обработка выбора действия
@router.message(ReviewStates.select_action)
async def process_review_action(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    action = message.text.strip().lower()
    try:
        if "оставить" in action or "1" in action:
            await start_create_review(message, state)
        elif "посмотреть" in action or "2" in action:
            await view_reviews(message, state)
        elif "редактировать" in action or "3" in action:
            await start_edit_review(message, state)
        else:
            await message.answer("Пожалуйста, выберите действие: 1, 2 или 3.")
    except Exception as e:
        logger.error(f"Ошибка при выборе действия с отзывами: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

# Создание нового отзыва
async def start_create_review(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        orders = await api_request("GET", f"{API_URL}order/", telegram_id)
        completed_orders = [o for o in orders if o["status"] == "Выполнен" and "review" not in o]
        if not completed_orders:
            await message.answer(
                "У вас нет завершённых заказов без отзывов.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
            return
        orders_list = "\n".join([f"ID: {o['id']} - {o['title']}" for o in completed_orders])
        await message.answer(
            f"Выберите заказ для отзыва:\n{orders_list}\n\nВведите ID заказа:",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.set_state(ReviewStates.select_order_create)
    except Exception as e:
        logger.error(f"Ошибка при загрузке завершённых заказов: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

@router.message(ReviewStates.select_order_create)
async def process_order_create(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        order_id = int(message.text.strip())
        order = await api_request("GET", f"{API_URL}order/{order_id}", telegram_id)
        if order["status"] != "Выполнен" or order["customer_id"] != telegram_id:
            await message.answer(
                "Этот заказ нельзя оценить.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
            return
        if "review" in order and order["review"]:
            await message.answer(
                "На этот заказ уже оставлен отзыв.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
            return
        await state.update_data(order_id=order_id, target_id=order["executor_id"])
        await message.answer("Введите рейтинг (от 1 до 5):")
        await state.set_state(ReviewStates.rating_create)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID заказа.")
    except Exception as e:
        logger.error(f"Ошибка при выборе заказа для отзыва: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

@router.message(ReviewStates.rating_create)
async def process_rating_create(message: Message, state: FSMContext):
    try:
        rating = int(message.text.strip())
        if not 1 <= rating <= 5:
            await message.answer("Пожалуйста, введите рейтинг от 1 до 5.")
            return
        await state.update_data(rating=rating)
        await message.answer("Введите комментарий (или отправьте пустое сообщение для пропуска):")
        await state.set_state(ReviewStates.comment_create)
    except ValueError:
        await message.answer("Пожалуйста, введите число от 1 до 5.")
    except Exception as e:
        logger.error(f"Ошибка при вводе рейтинга: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(message.from_user.id)))
        await state.clear()

@router.message(ReviewStates.comment_create)
async def process_comment_create(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        comment = message.text.strip() if message.text.strip() else None
        data = await state.get_data()
        review_data = {
            "order_id": data["order_id"],
            "target_id": data["target_id"],
            "rating": data["rating"],
            "comment": comment
        }
        review = await api_request("POST", f"{API_URL}review/", telegram_id, data=review_data)
        await message.answer(
            f"Отзыв для заказа ID {review['order_id']} успешно оставлен!\n"
            f"Рейтинг: {review['rating']}/5\n"
            f"Комментарий: {review['comment'] or 'Без комментария'}",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при создании отзыва: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

# Просмотр отзывов
async def view_reviews(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        reviews = await api_request("GET", f"{API_URL}review/", telegram_id)
        if not reviews:
            await message.answer(
                "У вас нет оставленных отзывов.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
            return
        reviews_list = "\n\n".join([
            f"ID: {r['id']} - Заказ ID: {r['order_id']}\n"
            f"Рейтинг: {r['rating']}/5\n"
            f"Комментарий: {r['comment'] or 'Без комментария'}"
            for r in reviews
        ])
        await message.answer(f"Ваши отзывы:\n{reviews_list}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при загрузке отзывов: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

# Редактирование отзыва
async def start_edit_review(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        reviews = await api_request("GET", f"{API_URL}review/", telegram_id)
        if not reviews:
            await message.answer(
                "У вас нет отзывов для редактирования.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
            return
        reviews_list = "\n".join([f"ID: {r['id']} - Заказ ID: {r['order_id']}" for r in reviews])
        await message.answer(
            f"Выберите отзыв для редактирования:\n{reviews_list}\n\nВведите ID отзыва:",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.set_state(ReviewStates.select_review_edit)
    except Exception as e:
        logger.error(f"Ошибка при загрузке отзывов для редактирования: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

@router.message(ReviewStates.select_review_edit)
async def process_review_edit(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        review_id = int(message.text.strip())
        review = await api_request("GET", f"{API_URL}review/{review_id}", telegram_id)
        if review["author_id"] != telegram_id:
            await message.answer(
                "Вы не можете редактировать этот отзыв.",
                reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
            )
            await state.clear()
            return
        await state.update_data(review_id=review_id)
        await message.answer(
            f"Текущий рейтинг: {review['rating']}/5\nВведите новый рейтинг (от 1 до 5):"
        )
        await state.set_state(ReviewStates.rating_edit)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID отзыва.")
    except Exception as e:
        logger.error(f"Ошибка при выборе отзыва для редактирования: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()

@router.message(ReviewStates.rating_edit)
async def process_rating_edit(message: Message, state: FSMContext):
    try:
        rating = int(message.text.strip())
        if not 1 <= rating <= 5:
            await message.answer("Пожалуйста, введите рейтинг от 1 до 5.")
            return
        await state.update_data(rating=rating)
        await message.answer("Введите новый комментарий (или отправьте пустое сообщение для пропуска):")
        await state.set_state(ReviewStates.comment_edit)
    except ValueError:
        await message.answer("Пожалуйста, введите число от 1 до 5.")
    except Exception as e:
        logger.error(f"Ошибка при редактировании рейтинга: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(message.from_user.id)))
        await state.clear()

@router.message(ReviewStates.comment_edit)
async def process_comment_edit(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        comment = message.text.strip() if message.text.strip() else None
        data = await state.get_data()
        review_data = {
            "rating": data["rating"],
            "comment": comment
        }
        review = await api_request("PATCH", f"{API_URL}review/{data['review_id']}", telegram_id, data=review_data)
        await message.answer(
            f"Отзыв ID {review['id']} успешно обновлён!\n"
            f"Рейтинг: {review['rating']}/5\n"
            f"Комментарий: {review['comment'] or 'Без комментария'}",
            reply_markup=get_main_keyboard(await get_user_roles(telegram_id))
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при обновлении отзыва: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard(await get_user_roles(telegram_id)))
        await state.clear()