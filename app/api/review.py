from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database.helper import get_session
from app.core.models.user import User
from app.core.services import review as review_service
from app.core.schemas.review import ReviewRead, ReviewCreate
from app.api.depends.user import get_current_user

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