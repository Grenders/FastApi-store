import pytest
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.config.dependencies import get_jwt_manager
from src.database.models.account import UserModel, UserGroupModel, UserGroupEnum
from src.database.models.product import CategoryModel, ProductModel, StockStatusEnum
from src.database.models.base import Base
from src.main import app
from src.database.engine import get_postgresql_db
from src.config.auth import get_current_user, security
from decimal import Decimal
import jwt
from datetime import datetime, timedelta, timezone


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

async def override_get_postgresql_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_postgresql_db] = override_get_postgresql_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_user_group():
    async with TestingSessionLocal() as session:
        group = UserGroupModel(name=UserGroupEnum.USER)
        session.add(group)
        await session.commit()
        await session.refresh(group)
        return group


@pytest.fixture
async def test_user(test_user_group):
    async with TestingSessionLocal() as session:
        user = UserModel.create(
            email="testuser@example.com",
            raw_password="testpassword123",
            group_id=test_user_group.id
        )
        user.is_active = True
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def auth_token(test_user):
    payload = {
        "email": test_user.email,
        "sub": str(test_user.id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    SECRET_KEY = "your-secret-key"
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


@pytest.fixture
def mock_jwt_manager(test_user):
    class MockJWTManager:
        def decode_access_token(self, token):
            try:
                payload = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
                return payload
            except jwt.PyJWTError:
                raise
    return MockJWTManager()


@pytest.fixture
def override_current_user(test_user, mock_jwt_manager):
    async def mock_get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_postgresql_db)
    ):
        return test_user
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_jwt_manager] = lambda: mock_jwt_manager
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_jwt_manager, None)


@pytest.fixture
async def sample_data():
    async with TestingSessionLocal() as session:
        category = CategoryModel(name="Electronics", description="Electronic gadgets")
        session.add(category)
        await session.commit()
        await session.refresh(category)

        products = [
            ProductModel(
                name=f"Product {i}",
                description=f"Description {i}",
                price=Decimal(f"{i * 10}.99"),
                stock=StockStatusEnum.AVAILABLE,
                category_id=category.id,
                image_url=f"http://example.com/product{i}.jpg",
            )
            for i in range(1, 25)
        ]
        session.add_all(products)
        await session.commit()
        return category, products