import logging
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from app.core.services.user import get_user_by_id, create_user
from app.core.schemas.user import UserCreate
from app.core.models.user import User
from app.bot.config import ADMIN_TELEGRAM_ID
from app.bot.handlers.utils import get_db_session, get_user_telegram_id

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


def get_main_keyboard(roles: dict = None):
    roles = roles or {}
    buttons = [
        [KeyboardButton(text="Профиль"), KeyboardButton(text="Создать заказ")],
        [KeyboardButton(text="Список заказов"), KeyboardButton(text="Сменить роль")]
    ]
    if roles.get("is_executor"):
        buttons.append([KeyboardButton(text="Создать предложение")])
    if roles.get("is_customer"):
        buttons.append([KeyboardButton(text="Посмотреть предложения")])
    if roles.get("is_admin"):
        buttons.append([KeyboardButton(text="Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, row_width=2)


@router.message(F.command == "start")
async def cmd_start(message: Message):
    telegram_id = get_user_telegram_id(message)
    logger.info(f"Получена команда /start от Telegram ID: {telegram_id}")
    session = next(get_db_session())
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            logger.info(f"Пользователь с Telegram ID {telegram_id} не найден, создаём нового.")
            user_data = UserCreate(
                telegram_id=telegram_id,
                name=message.from_user.full_name or "Без имени",
                username=message.from_user.username,
                is_customer=False,
                is_executor=False,
                city_id=1  # Предполагаем, что город с ID 1 (Кокшетау) существует
            )
            user = create_user(session, user_data)
            logger.info(f"Создан пользователь: {user.id}, {user.name}")
            await message.answer("Добро пожаловать! Вы зарегистрированы. Укажите роль через 'Сменить роль'.")
        else:
            logger.info(f"Пользователь найден: {user.id}, {user.name}")

        role = "Заказчик" if user.is_customer else "Исполнитель" if user.is_executor else "Не определена"
        city = user.city.name
        text = f"Добро пожаловать!\nИмя: {user.name}\nРоль: {role}\nГород: {city}\nРейтинг: {user.rating}"
        roles = {
            "is_admin": telegram_id == ADMIN_TELEGRAM_ID,
            "is_executor": user.is_executor,
            "is_customer": user.is_customer
        }
        await message.answer(text, reply_markup=get_main_keyboard(roles))
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())
    finally:
        session.close()


@router.message(F.text == "Профиль")
async def show_profile(message: Message):
    telegram_id = get_user_telegram_id(message)
    logger.info(f"Запрос профиля от Telegram ID: {telegram_id}")
    session = next(get_db_session())
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            logger.info(f"Пользователь с Telegram ID {telegram_id} не найден в профиле.")
            await message.answer("Пользователь не найден. Используйте /start для регистрации.")
            return
        role = "Заказчик" if user.is_customer else "Исполнитель" if user.is_executor else "Не определена"
        city = user.city.name
        text = f"Имя: {user.name}\nРоль: {role}\nГород: {city}\nРейтинг: {user.rating}"
        roles = {
            "is_admin": telegram_id == ADMIN_TELEGRAM_ID,
            "is_executor": user.is_executor,
            "is_customer": user.is_customer
        }
        await message.answer(text, reply_markup=get_main_keyboard(roles))
    except Exception as e:
        logger.error(f"Ошибка в профиле: {e}")
        await message.answer(f"Ошибка: {e}", reply_markup=get_main_keyboard())
    finally:
        session.close()

@router.message(lambda message: message.text not in ["/start", "Профиль", "Создать заказ", "Сменить роль"])
async def handle_random_text(message: Message):
    await message.answer("Пожалуйста, используйте команды или кнопки из меню.")