from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.core.models.category import Category
from app.core.schemas.category import CategoryCreate

def create_category(session: Session, data: CategoryCreate) -> Category:
    """Создать новую категорию."""
    category = Category(**data.model_dump())
    session.add(category)
    try:
        session.commit()
        session.refresh(category)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Category with this name already exists")
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create category: {e}")
    return category

def get_category_by_id(session: Session, id: int) -> Category:
    """Получить категорию по ID."""
    category = session.get(Category, id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

def get_all_categories(session: Session) -> list[Category]:
    """Получить список всех категорий."""
    stmt = select(Category)
    return session.scalars(stmt).all()