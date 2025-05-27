from typing import Optional
from fastapi import HTTPException
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
import re
from src.database.models.account import GenderEnum


class BaseEmailPasswordSchema(BaseModel):
    email: EmailStr
    password: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        errors = []

        if len(password) < 8:
            errors.append("Minimum 8 characters required")
        if not re.search(r"[A-Z]", password):
            errors.append("Must contain at least one uppercase letter")
        if not re.search(r"[a-z]", password):
            errors.append("Must contain at least one lowercase letter")
        if not re.search(r"\d", password):
            errors.append("Must contain at least one digit")
        if not re.search(r"[@$!%*?&#]", password):
            errors.append("Must contain at least one special character: @, $, !, %, *, ?, #, &")

        if errors:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Form contains errors",
                    "errors": {
                        "password": errors
                    }
                }
            )

        return password

class UserRegistrationRequestSchema(BaseEmailPasswordSchema):
    gender: Optional[GenderEnum] = None


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class PasswordResetCompleteRequestSchema(BaseEmailPasswordSchema):
    pass


class UserLoginRequestSchema(BaseEmailPasswordSchema):
    pass


class UserLoginResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRegistrationResponseSchema(BaseModel):
    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class MessageResponseSchema(BaseModel):
    message: str


class TokenRefreshRequestSchema(BaseModel):
    refresh_token: str


class TokenRefreshResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
