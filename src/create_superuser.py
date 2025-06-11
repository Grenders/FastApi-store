import asyncio
from getpass import getpass
import re
from sqlalchemy import select

from src.database.engine import AsyncPostgresqlSessionLocal
from src.database.models.account import UserModel, UserGroupModel, UserGroupEnum


def validate_password(password: str) -> list[str]:
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
        errors.append(
            "Must contain at least one special character: @, $, !, %, *, ?, #, &"
        )

    return errors


async def main():
    async with AsyncPostgresqlSessionLocal() as session:
        email = input("Email: ").strip().lower()
        password = getpass("Password: ")
        confirm_password = getpass("Confirm password: ")

        if password != confirm_password:
            print("❌ Passwords do not match.")
            return

        password_errors = validate_password(password)
        if password_errors:
            print("❌ Password validation failed:")
            for error in password_errors:
                print(f"   - {error}")
            return

        existing_user = await session.scalar(
            select(UserModel).where(UserModel.email == email)
        )
        if existing_user:
            print("❌ User with this email already exists.")
            return

        admin_group = await session.scalar(
            select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.ADMIN)
        )
        if not admin_group:
            admin_group = UserGroupModel(name=UserGroupEnum.ADMIN)
            session.add(admin_group)
            await session.flush()

        user = UserModel.create(
            email=email, raw_password=password, group_id=admin_group.id
        )
        user.is_active = True

        session.add(user)
        await session.commit()
        print("✅ Superuser created successfully!")


if __name__ == "__main__":
    asyncio.run(main())