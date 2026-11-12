from datetime import date

from sqlalchemy import JSON, Date, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    preparation_minutes: Mapped[int] = mapped_column(Integer)
    servings: Mapped[int] = mapped_column(Integer)
    ingredients: Mapped[list[dict]] = mapped_column(JSON)
    instructions: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[str] = mapped_column(String(32))
    unit: Mapped[str] = mapped_column(String(4))
    expiration_date: Mapped[date | None] = mapped_column(Date)
    minimum_stock: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)
