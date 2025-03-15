from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.core.models.category import Category
from app.core.schemas.category import CategoryCreate, CategoryUpdate

def create_category(session: Session, data: CategoryCreate) -> Category:
    """Создать новую категорию."""
    category = Category(**data.model_dump())
    session.add(category)
    try:
        session.commit()
        session.refresh(category)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Категория с таким названием уже существует")
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при создании категории: {e}")
    return category

def get_category_by_id(session: Session, id: int) -> Category:
    """Получить категорию по ID."""
    category = session.get(Category, id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category

def get_all_categories(session: Session) -> list[Category]:
    """Получить список всех категорий."""
    return session.scalars(select(Category)).all()

def update_category_by_id(session: Session, data: CategoryUpdate, id: int) -> Category:
    """Обновить данные категории по ID."""
    category = get_category_by_id(session, id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)
    try:
        session.commit()
        session.refresh(category)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Категория с таким названием уже существует")
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении категории: {e}")
    return category

def delete_category_by_id(session: Session, id: int):
    """Удалить категорию по ID."""
    category = get_category_by_id(session, id)
    session.delete(category)
    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении категории: {e}")