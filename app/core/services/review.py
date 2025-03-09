from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.core.models.review import Review
from app.core.schemas.review import ReviewCreate

def create_review(session: Session, data: ReviewCreate, author_id: int) -> Review:
    order = session.get(Order, data.order_id)
    if not order or order.customer_id != author_id or not order.is_completed:
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