from decimal import Decimal
from typing import List
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import String, ForeignKey, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship


from src.database import Base


class StockStatusEnum(str, Enum):
    AVAILABLE = "Available"
    NOT_AVAILABLE = "not available"


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    products: Mapped[list["Product"]] = relationship(
        back_populates="category", cascade="all, delete"
    )

    def __repr__(self):
        return f"<Category(name='{self.name}')>"

    def __str__(self):
        return self.name

    @classmethod
    def default_order_by(cls):
        return [cls.name.asc()]


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    stock: Mapped[StockStatusEnum] = mapped_column(
        SQLAlchemyEnum(StockStatusEnum), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False
    )
    category: Mapped["CategoryModel"] = relationship(
        "CategoryModel", back_populates="products"
    )
    image_url: Mapped[str] = mapped_column(String(255), nullable=True)
    cart_items: Mapped[List["CartItemModel"]] = relationship(back_populates="product")
    order_items: Mapped[List["OrderItemModel"]] = relationship(back_populates="product")

    def __repr__(self):
        return f"<Product(name='{self.name}')>"

    def __str__(self):
        return self.name

    @classmethod
    def default_order_by(cls):
        return [cls.name.asc()]
