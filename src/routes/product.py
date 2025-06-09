from decimal import Decimal

from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from starlette import status

from src.config.auth import get_current_admin_user, get_current_user
from src.database.models.account import UserModel
from src.schemas.product import (
    CategoryResponseSchema,
    CategoryListSchema,
    ProductCreateSchema,
    ProductUpdateSchema,
    ProductResponseSchema,
    ProductListSchema,
    ProductDetailSchema,
    CategoryCreateSchema,
    CategoryUpdateSchema,
    CartResponseSchema,
    CartListSchema,
    CartCreateSchema,
    CartDetailResponseSchema,
    CartItemCreateSchema,
    CartItemResponseSchema,
    CartItemUpdateSchema,
    OrderResponseSchema,
    OrderListResponseSchema,
)
from src.database.engine import get_postgresql_db
from src.database.models.product import (
    ProductModel,
    CategoryModel,
    CartModel,
    CartItemModel,
    OrderModel,
    OrderItemModel,
    StatusEnum,
)

router = APIRouter()


@router.get(
    "/products/",
    response_model=ProductResponseSchema,
    summary="Get a paginated list of products",
    responses={404: {"description": "No products found."}},
)
async def get_product_list(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(20, ge=1, le=20, description="Number of items per page"),
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    count_stmt = select(func.count(ProductModel.id))
    result_count = await db.execute(count_stmt)
    total_items = result_count.scalar() or 0

    if not total_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No products found."
        )

    stmt = select(ProductModel).options(selectinload(ProductModel.category))
    order_by = ProductModel.default_order_by()
    if order_by:
        stmt = stmt.order_by(*order_by)
    stmt = stmt.offset(offset).limit(per_page)

    result = await db.execute(stmt)
    products = result.scalars().all()
    if not products:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No products found."
        )

    product_list = [ProductListSchema.model_validate(product) for product in products]
    total_pages = (total_items + per_page - 1) // per_page

    return ProductResponseSchema(
        products=product_list,
        prev_page=(
            f"/products/?page={page - 1}&per_page={per_page}" if page > 1 else None
        ),
        next_page=(
            f"/products/?page={page + 1}&per_page={per_page}"
            if page < total_pages
            else None
        ),
        total_pages=total_pages,
        total_items=total_items,
    )


@router.post(
    "/products/",
    response_model=ProductDetailSchema,
    summary="Add new Product (admin only)",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Product created successfully."},
        400: {"description": "Invalid input or database error."},
        404: {"description": "Category not found."},
        422: {"description": "Validation error."},
    },
)
async def create_product(
    product_data: ProductCreateSchema,
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_admin_user),
) -> ProductDetailSchema:
    category = await db.scalar(
        select(CategoryModel).where(CategoryModel.id == product_data.category_id)
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found."
        )

    normalized_name = product_data.name.upper()
    existing = await db.scalar(
        select(ProductModel).where(ProductModel.name == normalized_name)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product with this name already exists.",
        )

    try:
        product = ProductModel(**product_data.model_dump())
        db.add(product)
        await db.flush()
        await db.commit()

        stmt = (
            select(ProductModel)
            .options(selectinload(ProductModel.category))
            .where(ProductModel.id == product.id)
        )
        result = await db.execute(stmt)
        product = result.scalar_one()

        return ProductDetailSchema.model_validate(product)
    except ValidationError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}",
        )
    except ValueError as e:
        await db.rollback()
        if "Price must be greater than 0" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price must be greater than 0.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid input: {str(e)}"
        )
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Database error: {str(e)}"
        )


@router.put(
    "/products/{product_id}",
    response_model=ProductDetailSchema,
    summary="Update an existing product (admin only)",
    responses={
        200: {"description": "Product updated successfully."},
        400: {"description": "Invalid input or update data."},
        404: {"description": "Product or category not found."},
        422: {"description": "Validation error."},
    },
)
async def update_product(
    product_id: int,
    product_data: ProductUpdateSchema,
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_admin_user),
) -> ProductDetailSchema:
    product = await db.scalar(select(ProductModel).where(ProductModel.id == product_id))
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found."
        )

    if product_data.category_id is not None:
        category = await db.scalar(
            select(CategoryModel).where(CategoryModel.id == product_data.category_id)
        )
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found."
            )

    if product_data.name and product_data.name != product.name:
        existing = await db.scalar(
            select(ProductModel).where(ProductModel.name == product_data.name)
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product with this name already exists.",
            )

    try:
        for field, value in product_data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        db.add(product)
        await db.commit()
        await db.refresh(product, ["category"])
        return ProductDetailSchema.model_validate(product)
    except ValidationError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}",
        )
    except ValueError as e:
        await db.rollback()
        if "Price must be greater than 0" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price must be greater than 0.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid input: {str(e)}"
        )
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Database error: {str(e)}"
        )


@router.delete(
    "/products/{product_id}",
    response_model=None,
    summary="Delete a product (admin only)",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Product deleted successfully."},
        403: {"description": "Admin access required."},
        404: {"description": "Product not found."},
    },
)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_admin_user),
):
    product = await db.scalar(select(ProductModel).where(ProductModel.id == product_id))
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found."
        )

    try:
        await db.delete(product)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete product: {str(e)}",
        )

    return None


@router.get(
    "/category/",
    response_model=CategoryResponseSchema,
    summary="Get a paginated list of categories",
    responses={404: {"description": "No categories found."}},
)
async def get_category_list(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(20, ge=1, le=20, description="Number of items per page"),
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    count_stmt = select(func.count(CategoryModel.id))
    result_count = await db.execute(count_stmt)
    total_items = result_count.scalar() or 0

    if not total_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No categories found."
        )

    stmt = select(CategoryModel).offset(offset).limit(per_page)
    result = await db.execute(stmt)
    categories = result.scalars().all()

    if not categories:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No categories found."
        )

    category_list = [CategoryListSchema.model_validate(cat) for cat in categories]
    total_pages = (total_items + per_page - 1) // per_page

    return CategoryResponseSchema(
        categories=category_list,
        prev_page=(
            f"/category/?page={page - 1}&per_page={per_page}" if page > 1 else None
        ),
        next_page=(
            f"/category/?page={page + 1}&per_page={per_page}"
            if page < total_pages
            else None
        ),
        total_pages=total_pages,
        total_items=total_items,
    )


@router.post(
    "/category/",
    response_model=CategoryListSchema,
    summary="Add new Category (admin only)",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Category created successfully."},
        400: {"description": "Invalid input."},
    },
)
async def create_category(
    category_data: CategoryCreateSchema,
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_admin_user),
) -> CategoryListSchema:
    exist_stmt = select(CategoryModel).where(CategoryModel.name == category_data.name)
    existing_result = await db.execute(exist_stmt)
    if existing_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists.",
        )

    try:
        category = CategoryModel(
            name=category_data.name, description=category_data.description
        )
        db.add(category)
        await db.commit()
        await db.refresh(category)

        return CategoryListSchema.model_validate(category)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid input data."
        )


@router.patch(
    "/category/{category_id}",
    response_model=CategoryListSchema,
    summary="Update info Category (admin only)",
    responses={
        200: {"description": "Category updated successfully."},
        400: {"description": "Invalid input or update data."},
        403: {"description": "Admin access required."},
        404: {"description": "Category not found."},
    },
)
async def update_category(
    category_id: int,
    category_data: CategoryUpdateSchema,
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_admin_user),
) -> CategoryListSchema:
    category = await db.scalar(
        select(CategoryModel).where(CategoryModel.id == category_id)
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found."
        )

    if category_data.name and category_data.name != category.name:
        existing = await db.scalar(
            select(CategoryModel).where(CategoryModel.name == category_data.name)
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists.",
            )

    try:
        for field, value in category_data.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(category, field, value)

        db.add(category)
        await db.commit()
        await db.refresh(category)
        return CategoryListSchema.model_validate(category)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Database error: {str(e)}"
        )


@router.delete(
    "/category/{category_id}",
    response_model=None,
    summary="Delete a category (admin only)",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Category deleted successfully."},
        403: {"description": "Admin access required."},
        404: {"description": "Category not found."},
    },
)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_admin_user),
):
    category = await db.scalar(
        select(CategoryModel).where(CategoryModel.id == category_id)
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found."
        )

    await db.delete(category)
    await db.commit()

    return


@router.get(
    "/cart/",
    response_model=CartResponseSchema,
    summary="Get a paginated list of carts for current user",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No carts found."}},
)
async def get_cart_list(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    count_stmt = select(func.count(CartModel.id)).where(
        CartModel.user_id == current_user.id
    )
    result_count = await db.execute(count_stmt)
    total_items = result_count.scalar() or 0

    if not total_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No carts found."
        )

    stmt = (
        select(CartModel)
        .options(selectinload(CartModel.cart_items).selectinload(CartItemModel.product))
        .where(CartModel.user_id == current_user.id)
        .offset(offset)
        .limit(per_page)
    )

    result = await db.execute(stmt)
    carts = result.scalars().all()

    if not carts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No carts found."
        )

    cart_list = [CartListSchema.model_validate(cart) for cart in carts]
    total_pages = (total_items + per_page - 1) // per_page

    return CartResponseSchema(
        carts=cart_list,
        prev_page=(f"/cart/?page={page - 1}&per_page={per_page}" if page > 1 else None),
        next_page=(
            f"/cart/?page={page + 1}&per_page={per_page}"
            if page < total_pages
            else None
        ),
        total_pages=total_pages,
        total_items=total_items,
    )


@router.post(
    "/cart/",
    response_model=CartDetailResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new cart with items",
    responses={
        400: {"description": "Invalid input"},
    },
)
async def create_cart(
    cart_data: CartCreateSchema,
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_user),
):
    new_cart = CartModel(user_id=current_user.id)
    db.add(new_cart)
    await db.flush()

    cart_items = []
    for item in cart_data.cart_items:
        product = await db.get(ProductModel, item.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product ID {item.product_id} not found",
            )

        cart_item = CartItemModel(
            cart_id=new_cart.id, product_id=item.product_id, quantity=item.quantity
        )
        cart_items.append(cart_item)

    db.add_all(cart_items)

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving cart: {str(e)}",
        )

    stmt = (
        select(CartModel)
        .options(selectinload(CartModel.cart_items).selectinload(CartItemModel.product))
        .where(CartModel.id == new_cart.id)
    )
    result = await db.execute(stmt)
    cart_with_items = result.scalar_one()

    return CartDetailResponseSchema.model_validate(cart_with_items)


@router.delete(
    "/cart/{cart_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete cart by ID",
    responses={
        404: {"description": "Cart not found."},
        403: {"description": "Not authorized to delete this cart."},
    },
)
async def delete_cart(
    cart_id: int,
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_user),
):
    result = await db.execute(select(CartModel).where(CartModel.id == cart_id))
    cart = result.scalar_one_or_none()

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found."
        )

    if cart.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this cart.",
        )

    await db.delete(cart)
    await db.commit()

    return


@router.post(
    "/cart/items/",
    response_model=CartItemResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add product to current user's cart",
    responses={
        404: {"description": "Cart or product not found."},
        403: {"description": "Not authorized to access this cart."},
        400: {"description": "Invalid data provided."},
    },
)
async def add_item_to_user_cart(
    item_data: CartItemCreateSchema,
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_user),
):
    result = await db.execute(
        select(CartModel).where(
            CartModel.user_id == current_user.id,
        )
    )
    cart = result.scalars().first()

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found for current user.",
        )

    product = await db.get(ProductModel, item_data.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product ID {item_data.product_id} not found.",
        )

    result = await db.execute(
        select(CartItemModel).where(
            CartItemModel.cart_id == cart.id,
            CartItemModel.product_id == item_data.product_id,
        )
    )
    existing_item = result.scalar_one_or_none()

    if existing_item:
        existing_item.quantity += item_data.quantity
        await db.commit()
        await db.refresh(existing_item)
        return CartItemResponseSchema.model_validate(existing_item)

    cart_item = CartItemModel(
        cart_id=cart.id,
        product_id=item_data.product_id,
        quantity=item_data.quantity,
    )
    db.add(cart_item)
    try:
        await db.commit()
        await db.refresh(cart_item)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving cart item: {str(e)}",
        )

    return CartItemResponseSchema.model_validate(cart_item)


@router.put(
    "/cart/items/{item_id}",
    response_model=CartItemResponseSchema,
    summary="Update quantity of a cart item by ID",
    responses={
        404: {"description": "Cart item not found"},
        403: {"description": "Not authorized to update this cart item"},
    },
)
async def update_cart_item(
    item_id: int,
    item_data: CartItemUpdateSchema,
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_user),
):
    stmt = (
        select(CartItemModel)
        .options(selectinload(CartItemModel.product), selectinload(CartItemModel.cart))
        .where(CartItemModel.id == item_id)
    )
    result = await db.execute(stmt)
    cart_item = result.scalar_one_or_none()

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found."
        )

    if cart_item.cart.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this item.",
        )

    cart_item.quantity = item_data.quantity

    try:
        await db.commit()
        await db.refresh(cart_item)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating cart item: {str(e)}",
        )

    return CartItemResponseSchema.model_validate(cart_item)


@router.delete(
    "/cart/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a cart item by ID",
    responses={
        404: {"description": "Cart item not found"},
        403: {"description": "Not authorized to delete this cart item"},
    },
)
async def delete_cart_item(
    item_id: int,
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_user),
):
    stmt = (
        select(CartItemModel)
        .options(selectinload(CartItemModel.cart))
        .where(CartItemModel.id == item_id)
    )
    result = await db.execute(stmt)
    cart_item = result.scalar_one_or_none()

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found."
        )

    if cart_item.cart.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this item.",
        )

    await db.delete(cart_item)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting cart item: {str(e)}",
        )

    return


@router.get(
    "/orders/",
    response_model=OrderListResponseSchema,
    summary="Get a paginated list of orders for current user",
    responses={404: {"description": "No orders found."}},
)
async def get_order_list(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_user),
):
    offset = (page - 1) * per_page

    count_stmt = select(func.count(OrderModel.id)).where(
        OrderModel.user_id == current_user.id
    )
    result_count = await db.execute(count_stmt)
    total_items = result_count.scalar() or 0

    if not total_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No orders found."
        )

    stmt = (
        select(OrderModel)
        .options(
            selectinload(OrderModel.order_items).selectinload(OrderItemModel.product)
        )
        .where(OrderModel.user_id == current_user.id)
        .offset(offset)
        .limit(per_page)
    )

    result = await db.execute(stmt)
    orders = result.scalars().all()

    if not orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No orders found."
        )

    orders_list = [OrderResponseSchema.model_validate(order) for order in orders]
    total_pages = (total_items + per_page - 1) // per_page

    return OrderListResponseSchema(
        orders=orders_list,
        prev_page=(
            f"/orders/?page={page - 1}&per_page={per_page}" if page > 1 else None
        ),
        next_page=(
            f"/orders/?page={page + 1}&per_page={per_page}"
            if page < total_pages
            else None
        ),
        total_pages=total_pages,
        total_items=total_items,
    )


@router.post(
    "/orders/",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create an order from current user's cart",
    responses={
        400: {"description": "Invalid input or empty cart"},
        404: {"description": "Cart or product not found"},
    },
)
async def create_order(
    session: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_user),
):
    stmt = (
        select(CartModel)
        .options(joinedload(CartModel.cart_items).joinedload(CartItemModel.product))
        .where(CartModel.user_id == current_user.id)
    )
    result = await session.execute(stmt)
    cart: CartModel = result.scalars().first()

    if not cart or not cart.cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty or not found.",
        )

    order_items = []
    total_price = Decimal("0")

    for item in cart.cart_items:
        product = item.product
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product ID {item.product_id} not found.",
            )
        if item.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid quantity for product {product.id}.",
            )
        order_item = OrderItemModel(
            product_id=product.id,
            quantity=item.quantity,
            price_at_order_time=Decimal(str(product.price)),
        )
        order_items.append(order_item)
        total_price += Decimal(str(product.price)) * item.quantity

    if total_price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total price must be greater than 0.",
        )

    order = OrderModel(
        user_id=current_user.id,
        total_price=total_price,
        status=StatusEnum.PROCESSING,
        order_items=order_items,
    )
    session.add(order)
    await session.flush()
    await session.delete(cart)
    await session.commit()

    stmt = (
        select(OrderModel)
        .options(
            selectinload(OrderModel.order_items).selectinload(OrderItemModel.product)
        )
        .where(OrderModel.id == order.id)
    )
    result = await session.execute(stmt)
    order = result.scalar_one()

    return OrderResponseSchema.model_validate(order)


@router.delete(
    "/orders/{order_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an order belonging to the current user",
    responses={
        204: {"description": "Order delete"},
        404: {"description": "Order not found successfully"},
    },
)
async def delete_order(
    order_id: int,
    session: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_user),
):
    stmt = select(OrderModel).where(
        OrderModel.id == order_id, OrderModel.user_id == current_user.id
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    await session.execute(
        delete(OrderItemModel).where(OrderItemModel.order_id == order.id)
    )

    await session.execute(delete(OrderModel).where(OrderModel.id == order.id))

    await session.commit()
    return
