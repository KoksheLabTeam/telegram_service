from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.services import review as review_service
from app.core.schemas.review import ReviewRead, ReviewCreate
from app.api.depends.user import get_current_user, get_admin_user
from fastapi.exceptions import HTTPException

router = APIRouter(prefix="/review", tags=["Review"])

@router.post("/", response_model=ReviewRead)
def create_review(
    data: ReviewCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    if not user.is_customer:
        raise HTTPException(status_code=403, detail="Only customers can create reviews")
    return review_service.create_review(session, data, user.id)

# Эндпоинт для удаления отзыва админом
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    id: int,
    admin: Annotated[User, Depends(get_admin_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Удалить отзыв (только для админа)."""
    review = session.get(Review, id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    session.delete(review)
    session.commit()