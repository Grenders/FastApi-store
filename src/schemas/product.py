from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, HttpUrl
from decimal import Decimal
from enum import Enum
from datetime import date

class StockStatusEnum(str, Enum):
    AVAILABLE = "Available"
    NOT_AVAILABLE = "not available"


class StatusEnum(str, Enum):
    PROCESSING = "processing"
    CANCELED = "canceled"
    CLOSED = "closed"


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

    class Config:
        from_attributes = True


class CategoryListSchema(CategoryBaseSchema):
    id: int

    class Config:
        from_attributes = True


class CategoryResponseSchema(BaseModel):
    category: List[CategoryListSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    class Config:
        from_attributes = True


class CategoryCreateSchema(CategoryBaseSchema):
    @field_validator("name", mode="before")
    @classmethod
    def normalize_name_category(cls, value: str) -> str:
        """
        Normalize name category
        """
        return value.upper()

class ProductBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    stock: StockStatusEnum
    category_id: int
    image_url: HttpUrl = Field(..., max_length=255)


class ProductListSchema(ProductBase):
    id: int

    class Config:
        from_attributes = True


class ProductDetailSchema(ProductBase):
    id: int
    category: CategoryBaseSchema

    class Config:
        from_attributes = True

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name_product(cls, value: str) -> str:
        return value.upper()


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

    class Config:
        from_attributes = True


class CartItemBaseSchema(BaseModel):
    product_id: int
    quantity: int


class CartItemCreateSchema(CartItemBaseSchema):
    pass


class CartItemResponseSchema(CartItemBaseSchema):
    id: int
    product: ProductListSchema


class Config:
    from_attributes = True


class CartResponseSchema(BaseModel):
    id: int
    user_id: int
    cart_items: List[CartItemResponseSchema]

    class Config:
        from_attributes = True




class OrderItemBaseSchema(BaseModel):
    product_id: int
    quantity: int
    price_at_order_time: Decimal


class OrderItemCreateSchema(OrderItemBaseSchema):
    pass


class OrderItemResponseSchema(OrderItemBaseSchema):
    id: int
    product: ProductResponseSchema

    class Config:
        from_attributes = True


class OrderResponseSchema(BaseModel):
    id: int
    user_id: int
    status: Optional[StatusEnum]
    created_at: Optional[date]
    total_price: Optional[Decimal]
    order_items: List[OrderItemResponseSchema]

    class Config:
        from_attributes = True
