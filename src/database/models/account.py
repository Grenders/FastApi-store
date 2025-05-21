from datetime import datetime, timezone, timedelta
from typing import List, Optional, TYPE_CHECKING
from enum import Enum

from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    func,
    Enum as SQLAlchemyEnum,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from passlib.context import CryptContext


from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.product import CartModel, OrderModel


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

    password_reset_token: Mapped[Optional["PasswordResetTokenModel"]] = relationship(
        "PasswordResetTokenModel", back_populates="user", cascade="all, delete-orphan"
    )

    refresh_tokens: Mapped[List["RefreshTokenModel"]] = relationship(
        "RefreshTokenModel", back_populates="user", cascade="all, delete-orphan"
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


class TokenBaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class PasswordResetTokenModel(TokenBaseModel):
    __tablename__ = "password_reset_tokens"

    user: Mapped[UserModel] = relationship(
        "UserModel", back_populates="password_reset_token"
    )

    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self):
        return f"<PasswordResetTokenModel(id={self.id}, token={self.token}, expires_at={self.expires_at})>"

    @classmethod
    def create(
        cls, user_id: int, token: str, hours_valid: int = 1
    ) -> "PasswordResetTokenModel":
        """
        Factory method to create a new PasswordResetTokenModel instance.

        Args:
            user_id: The ID of the user associated with the token.
            token: The reset token string.
            hours_valid: Number of hours the token is valid for (default: 1).

        Raises:
            ValueError: If hours_valid is not positive or token is empty.

        Returns:
            A new PasswordResetTokenModel instance.
        """
        if hours_valid <= 0:
            raise ValueError("hours_valid must be a positive integer")
        if not token:
            raise ValueError("Token cannot be empty")

        expires_at = datetime.now(timezone.utc) + timedelta(hours=hours_valid)
        return cls(user_id=user_id, token=token, expires_at=expires_at)


class RefreshTokenModel(TokenBaseModel):
    __tablename__ = "refresh_tokens"

    user: Mapped[UserModel] = relationship("UserModel", back_populates="refresh_tokens")
    token: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
    )

    @classmethod
    def create(
        cls, user_id: int | Mapped[int], days_valid: int, token: str
    ) -> "RefreshTokenModel":
        """
        Factory method to create a new RefreshTokenModel instance.

        This method simplifies the creation of a new refresh token by calculating
        the expiration date based on the provided number of valid days and setting
        the required attributes.
        """
        expires_at = datetime.now(timezone.utc) + timedelta(days=days_valid)
        return cls(user_id=user_id, expires_at=expires_at, token=token)

    def __repr__(self):
        return f"<RefreshTokenModel(id={self.id}, token={self.token}, expires_at={self.expires_at})>"
