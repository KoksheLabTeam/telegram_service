from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.core.models.user import User
from app.core.models.category import Category
from app.core.schemas.user import UserCreate, UserUpdate
from app.core.services.city import get_city_by_id
from app.api.depends.user import ADMIN_TELEGRAM_ID  # Добавлено

def create_user(session: Session, data: UserCreate) -> User:
    """Создать нового пользователя."""
    from app.api.depends.user import ADMIN_TELEGRAM_ID  # Импортируем здесь
    get_city_by_id(session, data.city_id)  # Проверка существования города
    user_data = data.model_dump(exclude={"category_ids"})  # Исключаем category_ids из данных
    # Устанавливаем is_admin=True, если telegram_id совпадает с ADMIN_TELEGRAM_ID
    if user_data["telegram_id"] == ADMIN_TELEGRAM_ID:
        user_data["is_admin"] = True
    user = User(**user_data)
    if data.category_ids:  # Если указаны категории
        categories = session.query(Category).filter(Category.id.in_(data.category_ids)).all()
        if len(categories) != len(data.category_ids):
            raise HTTPException(status_code=404, detail="Одна или несколько категорий не найдены")
        user.categories = categories
    session.add(user)
    try:
        session.commit()
        session.refresh(user)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Пользователь с таким telegram_id или username уже существует")
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при создании пользователя: {e}")
    return user

def get_user_by_id(session: Session, id: int) -> User:
    """Получить пользователя по ID."""
    user = session.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

def get_users(session: Session) -> list[User]:
    """Получить список всех пользователей."""
    return session.scalars(select(User)).all()

def update_user_by_id(session: Session, data: UserUpdate, id: int) -> User:
    """Обновить данные пользователя по ID."""
    from app.api.depends.user import ADMIN_TELEGRAM_ID  # Импортируем здесь
    user = get_user_by_id(session, id)
    update_data = data.model_dump(exclude_unset=True, exclude_none=True)
    if "city_id" in update_data:
        get_city_by_id(session, data.city_id)  # Проверка существования города
    if "category_ids" in update_data and data.category_ids is not None:
        categories = session.query(Category).filter(Category.id.in_(data.category_ids)).all()
        if len(categories) != len(data.category_ids):
            raise HTTPException(status_code=404, detail="Одна или несколько категорий не найдены")
        user.categories = categories
        del update_data["category_ids"]
    for key, value in update_data.items():
        setattr(user, key, value)
    # Синхронизируем is_admin с ADMIN_TELEGRAM_ID
    if user.telegram_id == ADMIN_TELEGRAM_ID:
        user.is_admin = True
    try:
        session.commit()
        session.refresh(user)
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении пользователя: {e}")
    return user

def delete_user_by_id(session: Session, id: int):
    """Удалить пользователя по ID."""
    user = get_user_by_id(session, id)
    session.delete(user)
    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении пользователя: {e}")