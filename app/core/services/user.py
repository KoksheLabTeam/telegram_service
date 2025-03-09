from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.core.models.user import User
from app.core.models.category import Category
from app.core.schemas.user import UserCreate, UserUpdate

def create_user(session: Session, data: UserCreate) -> User:
    user_data = data.model_dump(exclude={"category_ids"})
    user = User(**user_data)
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
    if "category_ids" in update_data:
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