from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    id: Mapped[int] = mapped_column(primary_key=True, index=True)