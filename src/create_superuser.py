import asyncio
from getpass import getpass
from sqlalchemy import select

import src.database.models.account
import src.database.models.product

from src.database.engine import AsyncPostgresqlSessionLocal
from src.database.models.account import UserModel, UserGroupModel, UserGroupEnum

async def main():
    async with AsyncPostgresqlSessionLocal() as session:
        email = input("Email: ").strip().lower()
        password = getpass("Password: ")
        confirm_password = getpass("Confirm password: ")

        if password != confirm_password:
            print("❌ Passwords do not match.")
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


        user = UserModel.create(email=email, raw_password=password, group_id=admin_group.id)
        user.is_active = True

        session.add(user)
        await session.commit()
        print("✅ Superuser created successfully!")

if __name__ == "__main__":
    asyncio.run(main())