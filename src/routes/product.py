from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from src.config.auth import get_current_admin_user, get_current_user
from src.database.models.account import UserModel, UserGroupEnum
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
)
from src.database.engine import get_postgresql_db
from src.database.models.product import ProductModel, CategoryModel

router = APIRouter()


@router.get(
    "/products/",
    response_model=ProductResponseSchema,
    summary="Get a paginated list of products",
    responses={404: {"description": "No products found."}},
)
async def get_product_list(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    count_stmt = select(func.count(ProductModel.id))
    result_count = await db.execute(count_stmt)
    total_items = result_count.scalar() or 0

    if not total_items:
        raise HTTPException(status_code=404, detail="No products found.")

    stmt = select(ProductModel).options(selectinload(ProductModel.category))
    order_by = ProductModel.default_order_by()
    if order_by:
        stmt = stmt.order_by(*order_by)
    stmt = stmt.offset(offset).limit(per_page)

    result = await db.execute(stmt)
    products = result.scalars().all()
    if not products:
        raise HTTPException(status_code=404, detail="No products found.")

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
    status_code=201,
    responses={
        201: {"description": "Product created successfully."},
        400: {"description": "Invalid input."},
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
        raise HTTPException(status_code=404, detail="Category not found.")

    existing = await db.scalar(
        select(ProductModel).where(ProductModel.name == product_data.name)
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Product with this name already exists."
        )

    try:
        product = ProductModel(**product_data.model_dump())
        db.add(product)
        await db.commit()
        await db.refresh(product, ["category"])
        return ProductDetailSchema.model_validate(product)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")


@router.put(
    "/products/{product_id}",
    response_model=ProductDetailSchema,
    summary="Update an existing product (admin only)",
    responses={
        200: {"description": "Product updated successfully."},
        400: {"description": "Invalid input or update data."},
        404: {"description": "Product or category not found."},
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
        raise HTTPException(status_code=404, detail="Product not found.")

    if product_data.category_id is not None:
        category = await db.scalar(
            select(CategoryModel).where(CategoryModel.id == product_data.category_id)
        )
        if not category:
            raise HTTPException(status_code=404, detail="Category not found.")

    if product_data.name and product_data.name != product.name:
        existing = await db.scalar(
            select(ProductModel).where(ProductModel.name == product_data.name)
        )
        if existing:
            raise HTTPException(
                status_code=400, detail="Product with this name already exists."
            )

    try:
        for field, value in product_data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        db.add(product)
        await db.commit()
        await db.refresh(product, ["category"])
        return ProductDetailSchema.model_validate(product)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")


@router.delete(
    "/products/{product_id}",
    response_model=None,
    summary="Delete a product (admin only)",
    status_code=204,
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
        raise HTTPException(status_code=404, detail="Product not found.")

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
    per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
    db: AsyncSession = Depends(get_postgresql_db),
    current_user: UserModel = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    count_stmt = select(func.count(CategoryModel.id))
    result_count = await db.execute(count_stmt)
    total_items = result_count.scalar() or 0

    if not total_items:
        raise HTTPException(status_code=404, detail="No categories found.")

    stmt = select(CategoryModel).offset(offset).limit(per_page)
    result = await db.execute(stmt)
    categories = result.scalars().all()

    if not categories:
        raise HTTPException(status_code=404, detail="No categories found.")

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
    status_code=201,
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
            status_code=400, detail="Category with this name already exists."
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
        raise HTTPException(status_code=400, detail="Invalid input data.")


@router.patch(
    "/category/{category_id}",
    response_model=CategoryListSchema,
    summary="Update info Category (admin only)",
    responses={
        200: {"description": "Category updated successfully."},
        400: {"description": "Invalid input or update data."},
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
        raise HTTPException(status_code=404, detail="Category not found.")

    if category_data.name and category_data.name != category.name:
        existing = await db.scalar(
            select(CategoryModel).where(CategoryModel.name == category_data.name)
        )
        if existing:
            raise HTTPException(
                status_code=400, detail="Category with this name already exists."
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
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")


@router.delete(
    "/category/{category_id}",
    response_model=None,
    summary="Delete a category (admin only)",
    status_code=204,
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
        raise HTTPException(status_code=404, detail="Category not found.")

    await db.delete(category)
    await db.commit()
    return
