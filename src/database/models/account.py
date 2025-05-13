from datetime import datetime
from typing import List, Optional
from enum import Enum

from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    func,
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from passlib.context import CryptContext
from pydantic import EmailStr

from src.database.models.base import Base


class UserGroupEnum(str, Enum):
    USER = "user"
    ADMIN = "admin"


class GenderEnum(str, Enum):
    MAN = "man"
    WOMAN = "woman"


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


class UserGroupModel(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[UserGroupEnum] = mapped_column(
        SQLAlchemyEnum(UserGroupEnum, native_enum=False), nullable=False, unique=True
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
    gender: Mapped[Optional[GenderEnum]] = mapped_column(
        SQLAlchemyEnum(GenderEnum, native_enum=False), nullable=True
    )
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

    carts: Mapped[List["CartModel"]] = relationship("CartModel", back_populates="user")
    orders: Mapped[List["OrderModel"]] = relationship(
        "OrderModel", back_populates="user"
    )

    def __repr__(self):
        return (
            f"<UserModel(id={self.id}, email={self.email}, is_active={self.is_active})>"
        )

    @classmethod
    def create(cls, email: str, raw_password: str, group_id: int) -> "UserModel":
        if not email:
            raise ValueError("Email cannot be empty.")
        if not raw_password:
            raise ValueError("Password cannot be empty.")

        user = cls(email=email.lower(), group_id=group_id)
        user.password = raw_password
        return user

    @property
    def password(self) -> None:
        raise AttributeError(
            "Password is write-only. Use the setter to set the password."
        )

    @password.setter
    def password(self, raw_password: str) -> None:
        if len(raw_password) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        self._hashed_password = hash_password(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        return verify_password(raw_password, self._hashed_password)

    @validates("email")
    def validate_email(self, _, value: str) -> str:
        try:
            return str(EmailStr(value.lower()))
        except ValueError as e:
            raise ValueError(f"Invalid email: {value}") from e
