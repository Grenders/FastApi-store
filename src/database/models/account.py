from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from enum import Enum
from pydantic import validators
from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    func,
    ForeignKey,
    UniqueConstraint,
    Numeric,
)
from sqlalchemy.orm import mapped_column, Mapped, relationship, validates

from src.database import Base

from security.passwords import hash_password, verify_password


class UserGroupEnum(str, Enum):
    USER = "user"
    ADMIN = "admin"


class GenderEnum(str, Enum):
    MAN = "man"
    WOMAN = "woman"


class StatusEnum(str, Enum):
    PROCESSING = "processing"
    CANCELED = "canceled"
    CLOSED = "closed"


class UserGroupModel(Base):
    """
    A model for user groups that defines roles (for example, USER, ADMIN)
    """
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[UserGroupEnum] = mapped_column(
        Enum(UserGroupEnum), nullable=False, unique=True
    )

    users: Mapped[List["UserModel"]] = relationship("UserModel", back_populates="group")

    def __repr__(self):
        return f"<UserGroupModel(id={self.id}, name={self.name})>"

    def __str__(self):
        return self.name.value


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    _hashed_password: Mapped[str] = mapped_column(
        "hashed_password", String(255), nullable=False
    )
    gender: Mapped[Optional[GenderEnum]] = mapped_column(Enum(GenderEnum))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    group_id: Mapped[int] = mapped_column(
        ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group: Mapped["UserGroupModel"] = relationship(
        "UserGroupModel", back_populates="users"
    )
    carts: Mapped[List["CartModel"]] = relationship(back_populates="user")
    orders: Mapped[List["OrderModel"]] = relationship(back_populates="user")

    def __repr__(self):
        return (
            f"<UserModel(id={self.id}, email={self.email}, is_active={self.is_active})>"
        )

    @classmethod
    def create(
        cls, email: str, raw_password: str, group_id: int
    ) -> "UserModel":
        """
        Method to create a new UserModel
        """
        if not email:
            raise ValueError("Email cannot be empty.")
        if not raw_password:
            raise ValueError("Password cannot be empty.")

        user = cls(email=email, group_id=group_id)
        user.password = raw_password
        return user

    @property
    def password(self) -> None:
        raise AttributeError(
            "Password is write-only. Use the setter to set the password."
        )

    @password.setter
    def password(self, raw_password: str) -> None:
        """
        Set the user's password after validating its strength and hashing it.
        """
        validators.validate_password_strength(raw_password)
        self._hashed_password = hash_password(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        """
        Verify the provided password against the stored hashed password.
        """
        return verify_password(raw_password, self._hashed_password)

    @validates("email")
    def validate_email(self, value):
        return validators.validate_email(value.lower())


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="carts")
    cart_items: Mapped[List["CartItemModel"]] = relationship(back_populates="cart")

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
    def validate_quantity(self, value):
        if value <= 0:
            raise ValueError("Quantity must be greater than 0.")
        return value


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="orders")
    status: Mapped[StatusEnum] = mapped_column(
        Enum(StatusEnum), default=StatusEnum.PROCESSING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    total_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    order_items: Mapped[List["OrderItemModel"]] = relationship(back_populates="order")

    def __repr__(self):
        return f"<OrderModel(id={self.id})>"

    @validates("total_price")
    def validate_total_price(self, value):
        if value <= 0:
            raise ValueError("Total price must be greater than 0.")
        return value


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), nullable=False, index=True
    )
    order: Mapped["OrderModel"] = relationship(back_populates="order_items")
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    product: Mapped["ProductModel"] = relationship(back_populates="order_items")
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