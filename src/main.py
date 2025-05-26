from contextlib import asynccontextmanager

from fastapi import FastAPI
from src.routes.product import router as product_router
from src.routes.account import router as account_router

from src.database.engine import get_postgresql_db_contextmanager, init_user_groups


@asynccontextmanager
async def lifespan(_: FastAPI):

    async with get_postgresql_db_contextmanager() as db:
        await init_user_groups(db)
    yield


app = FastAPI(
    title="Order Management API",
    description="REST API for online store orders",
    lifespan=lifespan,
)

api_version_prefix = "/api"

app.include_router(
    product_router, prefix=f"{api_version_prefix}/v1", tags=["products"]
)
app.include_router(
    account_router, prefix=f"{api_version_prefix}/v1/accounts", tags=["accounts"]
)
