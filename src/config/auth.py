from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.config.dependencies import get_jwt_manager
from src.database.engine import get_postgresql_db
from src.database.models.account import UserModel, UserGroupEnum


security = HTTPBearer()


async def _get_user_from_token(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession,
    jwt_manager,
) -> UserModel:
    token = credentials.credentials
    try:
        payload = jwt_manager.decode_access_token(token)
        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing email",
            )
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    stmt = (
        select(UserModel)
        .options(selectinload(UserModel.group))
        .where(UserModel.email == email)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found",
        )

    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_postgresql_db),
    jwt_manager=Depends(get_jwt_manager),
) -> UserModel:

    user = await _get_user_from_token(credentials, db, jwt_manager)
    if user.group.name not in [UserGroupEnum.USER, UserGroupEnum.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Requires USER or ADMIN role.",
        )
    return user


async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_postgresql_db),
    jwt_manager=Depends(get_jwt_manager),
) -> UserModel:
    user = await _get_user_from_token(credentials, db, jwt_manager)
    if user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return user
