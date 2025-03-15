from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.models.base import Base

class City(Base):
    """Модель города."""
    __tablename__ = "cities"

    name: Mapped[str] = mapped_column(unique=True, nullable=False)  # Название города (уникальное)
    users: Mapped[list["User"]] = relationship("User", back_populates="city")  # Пользователи, привязанные к городу