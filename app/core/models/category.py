from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.models.base import Base

class Category(Base):
    """Модель для категорий услуг."""
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    users: Mapped[list["User"]] = relationship(
        "User", secondary="user_categories", back_populates="categories"
    )