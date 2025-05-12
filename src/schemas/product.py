from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, HttpUrl, ConfigDict
from decimal import Decimal
from datetime import date

from src.database.models.product import StockStatusEnum, StatusEnum


# ------------------ CATEGORY ------------------

class CategoryBaseSchema(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    products: Optional[List["ProductListSchema"]] = None

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Category name cannot be empty or whitespace")
        return value

    model_config = ConfigDict(from_attributes=True)


class CategoryListSchema(CategoryBaseSchema):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CategoryResponseSchema(BaseModel):
    category: List[CategoryListSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    model_config = ConfigDict(from_attributes=True)


class CategoryCreateSchema(CategoryBaseSchema):
    @field_validator("name", mode="before")
    @classmethod
    def normalize_name_category(cls, value: str) -> str:
        return value.upper()


# ------------------ PRODUCT ------------------

class ProductBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    stock: StockStatusEnum
    category_id: int
    image_url: HttpUrl = Field(..., max_length=255)


class ProductListSchema(ProductBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ProductDetailSchema(ProductBase):
    id: int
    category: CategoryBaseSchema

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name_product(cls, value: str) -> str:
        return value.upper()

    model_config = ConfigDict(from_attributes=True)


class ProductCreateSchema(ProductBase):
    @field_validator("name", mode="before")
    @classmethod
    def normalize_name_product(cls, value: str) -> str:
        return value.upper()


class ProductUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    stock: Optional[StockStatusEnum] = None
    category_id: Optional[int] = None
    image_url: Optional[HttpUrl] = None


class ProductResponseSchema(BaseModel):
    products: List[ProductListSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    model_config = ConfigDict(from_attributes=True)


# ------------------ CART ------------------

class CartItemBaseSchema(BaseModel):
    product_id: int
    quantity: int


class CartItemCreateSchema(CartItemBaseSchema):
    pass


class CartItemResponseSchema(CartItemBaseSchema):
    id: int
    product: ProductListSchema

    model_config = ConfigDict(from_attributes=True)


class CartBaseSchema(BaseModel):
    user_id: int


class CartCreateSchema(CartBaseSchema):
    cart_items: List[CartItemCreateSchema]


class CartResponseSchema(BaseModel):
    id: int
    user_id: int
    cart_items: List[CartItemResponseSchema]

    model_config = ConfigDict(from_attributes=True)


# ------------------ ORDER ------------------

class OrderItemBaseSchema(BaseModel):
    product_id: int
    quantity: int
    price_at_order_time: Decimal


class OrderItemCreateSchema(OrderItemBaseSchema):
    pass


class OrderItemResponseSchema(OrderItemBaseSchema):
    id: int
    product: ProductListSchema

    model_config = ConfigDict(from_attributes=True)


class OrderBaseSchema(BaseModel):
    user_id: int
    status: Optional[StatusEnum] = StatusEnum.PROCESSING
    total_price: Decimal
    order_items: List[OrderItemCreateSchema]


class OrderCreateSchema(OrderBaseSchema):
    pass


class OrderResponseSchema(BaseModel):
    id: int
    user_id: int
    status: Optional[StatusEnum]
    created_at: Optional[date]
    total_price: Optional[Decimal]
    order_items: List[OrderItemResponseSchema]

    model_config = ConfigDict(from_attributes=True)


# ------------------ Forward Refs ------------------

CategoryBaseSchema.model_rebuild()
