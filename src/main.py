from fastapi import FastAPI
from src.routes.product import router as product_router

app = FastAPI(
    title="Order Management API", description="REST API for online store orders"
)

api_version_prefix = "/api"

app.include_router(
    product_router, prefix=f"{api_version_prefix}/products", tags=["products"]
)
