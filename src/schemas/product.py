from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from decimal import Decimal
from datetime import datetime

from src.database.models.product import StockStatusEnum, StatusEnum


class CategoryBaseSchema(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Category name cannot be empty or whitespace")
        return value

    model_config = ConfigDict(from_attributes=True)


class CategoryListSchema(CategoryBaseSchema):
    id: int


class CategoryResponseSchema(BaseModel):
    categories: List[CategoryListSchema]
    prev_page: Optional[str] = None
    next_page: Optional[str] = None
    total_pages: int
    total_items: int

    model_config = ConfigDict(from_attributes=True)


class CategoryCreateSchema(CategoryBaseSchema):
    pass


class CategoryUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name_not_empty(cls, value: Optional[str]) -> Optional[str]:
        if value and not value.strip():
            raise ValueError("Category name cannot be empty or whitespace")
        return value

    model_config = ConfigDict(from_attributes=True)




class ProductBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    stock: StockStatusEnum
    category_id: int
    image_url: str = Field(..., max_length=255)

    model_config = ConfigDict(from_attributes=True)


class ProductListSchema(ProductBase):
    id: int


class ProductDetailSchema(ProductBase):
    id: int
    category: CategoryBaseSchema

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name_product(cls, value: str) -> str:
        return value.upper()


class ProductCreateSchema(ProductBase):
    @field_validator("name", mode="before")
    @classmethod
    def normalize_name_product(cls, value: str) -> str:
        return value.upper()

    @field_validator("image_url", mode="before")
    @classmethod
    def normalize_image_url(cls, value: str) -> str:
        return str(value)


class ProductUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    stock: Optional[StockStatusEnum] = None
    category_id: Optional[int] = None
    image_url: Optional[str] = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name_product(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else None

    @field_validator("image_url", mode="before")
    @classmethod
    def normalize_image_url(cls, value: Optional[str]) -> Optional[str]:
        return str(value) if value else None

    model_config = ConfigDict(from_attributes=True)


class ProductResponseSchema(BaseModel):
    products: List[ProductListSchema]
    prev_page: Optional[str] = None
    next_page: Optional[str] = None
    total_pages: int
    total_items: int

    model_config = ConfigDict(from_attributes=True)




class CartItemBaseSchema(BaseModel):
    product_id: int
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class CartItemCreateSchema(CartItemBaseSchema):
    pass


class CartItemResponseSchema(CartItemBaseSchema):
    id: int
    product: ProductListSchema

    model_config = ConfigDict(from_attributes=True)


class CartBaseSchema(BaseModel):


    model_config = ConfigDict(from_attributes=True)


class CartListSchema(BaseModel):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class CartCreateSchema(CartBaseSchema):
    cart_items: List[CartItemCreateSchema]

    model_config = ConfigDict(from_attributes=True)

class CartDetailResponseSchema(BaseModel):
    id: int
    user_id: int
    cart_items: List[CartItemResponseSchema]

    model_config = ConfigDict(from_attributes=True)

class CartResponseSchema(BaseModel):
    carts: List[CartListSchema]
    total_pages: int
    total_items: int
    prev_page: Optional[str] = None
    next_page: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ------------------ ORDER ------------------


class OrderItemBaseSchema(BaseModel):
    product_id: int
    quantity: int
    price_at_order_time: Decimal

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class OrderCreateSchema(OrderBaseSchema):
    pass


class OrderResponseSchema(BaseModel):
    id: int
    user_id: int
    status: Optional[StatusEnum]
    created_at: Optional[datetime]
    total_price: Optional[Decimal]
    order_items: List[OrderItemResponseSchema]

    model_config = ConfigDict(from_attributes=True)


# ------------------ Forward Refs ------------------

CategoryBaseSchema.model_rebuild()
