from decimal import Decimal
from datetime import datetime
from typing import List, TYPE_CHECKING
from enum import Enum

from sqlalchemy import (
    Integer,
    String,
    Numeric,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    func,
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from src.database.models.base import Base
from src.database.models.account import UserModel

if TYPE_CHECKING:
    from src.database.models.account import UserModel


class StatusEnum(str, Enum):
    PROCESSING = "processing"
    CANCELED = "canceled"
    CLOSED = "closed"


class StockStatusEnum(str, Enum):
    AVAILABLE = "Available"
    NOT_AVAILABLE = "not available"


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    products: Mapped[List["ProductModel"]] = relationship(
        "ProductModel", back_populates="category", cascade="all, delete"
    )

    def __repr__(self):
        return f"<Category(name='{self.name}')>"


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    stock: Mapped[StockStatusEnum] = mapped_column(
        SQLAlchemyEnum(StockStatusEnum, native_enum=False), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped["CategoryModel"] = relationship(
        "CategoryModel", back_populates="products"
    )
    image_url: Mapped[str] = mapped_column(String(255), nullable=True)
    cart_items: Mapped[List["CartItemModel"]] = relationship(
        "CartItemModel", back_populates="product"
    )
    order_items: Mapped[List["OrderItemModel"]] = relationship(
        "OrderItemModel", back_populates="product"
    )

    def __repr__(self):
        return f"<Product(name='{self.name}')>"


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="carts")
    cart_items: Mapped[List["CartItemModel"]] = relationship(
        "CartItemModel",
        back_populates="cart",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<CartModel(id={self.id})>"


class CartItemModel(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id"), nullable=False, index=True
    )
    cart: Mapped["CartModel"] = relationship("CartModel", back_populates="cart_items")
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    product: Mapped["ProductModel"] = relationship(
        "ProductModel", back_populates="cart_items"
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint("cart_id", "product_id"),)

    def __repr__(self):
        return f"<CartItemModel(id={self.id})>"

    @validates("quantity")
    def validate_quantity(self, key, value):
        if value <= 0:
            raise ValueError("Quantity must be greater than 0.")
        return value


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="orders")
    status: Mapped[StatusEnum] = mapped_column(
        SQLAlchemyEnum(StatusEnum, native_enum=False),
        default=StatusEnum.PROCESSING,
        server_default=StatusEnum.PROCESSING.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    total_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    order_items: Mapped[List["OrderItemModel"]] = relationship(
        "OrderItemModel", back_populates="order"
    )

    def __repr__(self):
        return f"<OrderModel(id={self.id})>"

    @validates("total_price")
    def validate_total_price(self, _, value):
        if value <= 0:
            raise ValueError("Total price must be greater than 0.")
        return value


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), nullable=False, index=True
    )
    order: Mapped["OrderModel"] = relationship(
        "OrderModel", back_populates="order_items"
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    product: Mapped["ProductModel"] = relationship(
        "ProductModel", back_populates="order_items"
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_at_order_time: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    __table_args__ = (UniqueConstraint("order_id", "product_id"),)

    def __repr__(self):
        return f"<OrderItemModel(id={self.id})>"

    @validates("quantity")
    def validate_quantity(self, value):
        if value <= 0:
            raise ValueError("Quantity must be greater than 0.")
        return value

    @validates("price_at_order_time")
    def validate_price(self, value):
        if value < 0:
            raise ValueError("Price at order time cannot be negative.")
        return value
