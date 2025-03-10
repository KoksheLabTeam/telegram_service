from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.core.models.user import User
from app.core.models.category import Category
from app.core.schemas.user import UserCreate, UserUpdate
from app.core.services.city import get_city_by_id

def create_user(session: Session, data: UserCreate) -> User:
    # Проверяем, что is_customer и is_executor не активны одновременно
    if data.is_customer and data.is_executor:
        raise HTTPException(status_code=400, detail="User cannot be both customer and executor")
    # Проверяем, существует ли город
    get_city_by_id(session, data.city_id)
    user_data = data.model_dump(exclude={"category_ids"})
    user = User(**user_data)
    # Категории временно не проверяем и не добавляем
    if data.category_ids:  # Если категории переданы, добавляем их
        categories = session.query(Category).filter(Category.id.in_(data.category_ids)).all()
        if len(categories) != len(data.category_ids):
            raise HTTPException(status_code=404, detail="One or more categories not found")
        user.categories = categories
    session.add(user)
    try:
        session.commit()
        session.refresh(user)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="User with this telegram_id or username already exists")
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create user: {e}")
    return user

def get_user_by_id(session: Session, id: int) -> User:
    user = session.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def update_user_by_id(session: Session, data: UserUpdate, id: int) -> User:
    user = get_user_by_id(session, id)
    update_data = data.model_dump(exclude_unset=True, exclude_none=True)
    if "is_customer" in update_data or "is_executor" in update_data:
        is_customer = update_data.get("is_customer", user.is_customer)
        is_executor = update_data.get("is_executor", user.is_executor)
        if is_customer and is_executor:
            raise HTTPException(status_code=400, detail="User cannot be both customer and executor")
    if "city_id" in update_data:
        get_city_by_id(session, data.city_id)
    if "category_ids" in update_data and data.category_ids is not None:
        categories = session.query(Category).filter(Category.id.in_(data.category_ids)).all()
        if len(categories) != len(data.category_ids):
            raise HTTPException(status_code=404, detail="One or more categories not found")
        user.categories = categories
        del update_data["category_ids"]
    for key, value in update_data.items():
        setattr(user, key, value)
    try:
        session.commit()
        session.refresh(user)
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update user: {e}")
    return user