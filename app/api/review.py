from typing import Annotated, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.services import review as review_service
from app.core.schemas.review import ReviewRead, ReviewCreate, ReviewUpdate
from app.api.depends.user import get_current_user, get_admin_user

router = APIRouter(prefix="/review", tags=["Review"])  # Маршруты для отзывов

@router.post("/", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
def create_review(
    data: ReviewCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Создать новый отзыв (доступно только заказчикам)."""
    if not user.is_customer:
        raise HTTPException(status_code=403, detail="Только заказчики могут создавать отзывы")
    return review_service.create_review(session, data, user.id)

@router.get("/", response_model=List[ReviewRead])
def get_reviews(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Получить список отзывов текущего пользователя."""
    return review_service.get_reviews_by_user(session, current_user.id)

@router.get("/{id}", response_model=ReviewRead)
def get_review(
    id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Получить отзыв по ID."""
    review = review_service.get_review_by_id(session, id)
    if review.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет прав для просмотра этого отзыва")
    return review

@router.patch("/{id}", response_model=ReviewRead)
def update_review(
    id: int,
    data: ReviewUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Обновить отзыв (доступно только автору)."""
    review = review_service.get_review_by_id(session, id)
    if review.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Только автор может обновлять этот отзыв")
    return review_service.update_review_by_id(session, data, id)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    id: int,
    admin: Annotated[User, Depends(get_admin_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Удалить отзыв (доступно только администратору)."""
    review_service.delete_review_by_id(session, id)