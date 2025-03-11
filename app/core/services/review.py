from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.core.models.review import Review
from app.core.models.order import Order
from app.core.schemas.review import ReviewCreate, ReviewUpdate

def create_review(session: Session, data: ReviewCreate, author_id: int) -> Review:
    order = session.get(Order, data.order_id)
    if not order or order.customer_id != author_id or order.status != "completed":
        raise HTTPException(status_code=400, detail="Invalid or incomplete order")
    review_data = data.model_dump()
    review = Review(**review_data, author_id=author_id)
    session.add(review)
    try:
        session.commit()
        session.refresh(review)
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create review: {e}")
    return review

def get_review_by_id(session: Session, id: int) -> Review:
    review = session.get(Review, id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review

def get_reviews_by_user(session: Session, user_id: int) -> list[Review]:
    stmt = select(Review).where(Review.author_id == user_id)
    return session.scalars(stmt).all()

def update_review_by_id(session: Session, data: ReviewUpdate, id: int) -> Review:
    review = get_review_by_id(session, id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(review, key, value)
    try:
        session.commit()
        session.refresh(review)
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update review: {e}")
    return review

def delete_review_by_id(session: Session, id: int):
    review = get_review_by_id(session, id)
    session.delete(review)
    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete review: {e}")