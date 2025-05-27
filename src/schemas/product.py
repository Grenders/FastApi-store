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
    price: Decimal = Field(..., gt=0)
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
    price: Optional[Decimal] = Field(None, gt=0)
    stock: Optional[StockStatusEnum] = None
    category_id: Optional[int] = None
    image_url: Optional[str] = None

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is not None and value <= 0:
            raise ValueError("Price must be greater than 0")
        return value

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


class CartItemUpdateSchema(BaseModel):
    quantity: int

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Quantity must be greater than 0.")
        return value

    model_config = ConfigDict(from_attributes=True)


class CartItemResponseSchema(CartItemBaseSchema):
    id: int
    product: ProductListSchema

    model_config = ConfigDict(from_attributes=True)


class CartBaseSchema(BaseModel):

    model_config = ConfigDict(from_attributes=True)


class ProductInCartSchema(BaseModel):
    id: int
    name: str
    price: float

    model_config = ConfigDict(from_attributes=True)


class CartItemSchema(BaseModel):
    id: int
    product: ProductInCartSchema
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class CartListSchema(BaseModel):
    id: int
    cart_items: list[CartItemSchema]

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
    quantity: int = Field(..., gt=0)

    model_config = ConfigDict(from_attributes=True)


class OrderItemCreateSchema(OrderItemBaseSchema):
    pass


class OrderItemResponseSchema(OrderItemBaseSchema):
    id: int
    product: ProductListSchema

    model_config = ConfigDict(from_attributes=True)


class OrderBaseSchema(BaseModel):
    status: Optional[StatusEnum] = StatusEnum.PROCESSING
    order_items: List[OrderItemCreateSchema]

    model_config = ConfigDict(from_attributes=True)


class OrderCreateSchema(OrderBaseSchema):
    pass


class OrderResponseSchema(BaseModel):
    id: int
    user_id: int
    status: StatusEnum
    created_at: datetime
    total_price: Decimal
    order_items: List[OrderItemResponseSchema]

    model_config = ConfigDict(from_attributes=True)


class OrderListResponseSchema(BaseModel):
    orders: List[OrderResponseSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int


class TokenRefreshRequestSchema(BaseModel):
    refresh_token: str


class TokenRefreshResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
