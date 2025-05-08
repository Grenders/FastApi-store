from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.product import CategoryResponseSchema, CategoryListSchema
from src.database.engine import get_postgresql_db
from src.database.models.product import ProductModel, CategoryModel

from src.schemas.product import (
    ProductCreateSchema,
    ProductUpdateSchema,
    ProductResponseSchema,
    ProductListSchema,
    ProductDetailSchema
)

router = APIRouter()


@router.get(
    "/products/",
    response_model=ProductResponseSchema,
    summary="Get a paginated list of products",
    responses={
        404: {
            "description": "No product found.",
        },
    },
)
async def get_product_list(
        page: int = Query(1, ge=1, description="Page number (1-based index)"),
        per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
        db: AsyncSession = Depends(get_postgresql_db),
):
    """
    Fetch a paginated list of products from the database (asynchronously).

    This function retrieves a paginated list of products, allowing the client to specify
    the page number and the number of items per page. It calculates the total pages
    and provides links to the previous and next pages when applicable.

    :param page: The page number to retrieve (1-based index, must be >= 1).
    :type page: int
    :param per_page: The number of items to display per page (must be between 1 and 20).
    :type per_page: int
    :param db: The async SQLAlchemy database session (provided via dependency injection).
    :type db: AsyncSession

    :return: A response containing the paginated list of products and metadata.
    :rtype: ProductResponseSchema

    :raises HTTPException: Raises a 404 error if no products are found for the requested page.
    """
    offset = (page - 1) * per_page

    count_stms = select(func.count(ProductModel.id))
    result_count = await db.execute(count_stms)
    total_items = result_count.scalar() or 0
    if not total_items:
        raise HTTPException(status_code=404, detail="No products found.")

    order_by = ProductModel.default_order_by()
    stmt = select(ProductModel)
    if order_by:
        stmt = stmt.order_by(*order_by)

    stmt = stmt.offset(offset).limit(per_page)
    result_products = await db.execute(stmt)
    products = result_products.scalars().all()

    if not products:
        raise HTTPException(status_code=404, detail="No products found.")

    products_list = [ProductListSchema.model_validate(product) for product in products]

    total_pages = (total_items + per_page - 1) // per_page
    return ProductResponseSchema(
        products=products_list,
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
    summary="Add new Product",
    description=(
            "<h3>This endpoint allows clients to add a new product to the database. "
    ),
    responses={
        201: {
            "description": "Product created successfully.",
        },
        400: {
            "description": "Invalid input.",
        },

    },
    status_code=201
)
async def create_product(
        product_data: ProductCreateSchema,
        db: AsyncSession = Depends(get_postgresql_db)
) -> ProductDetailSchema:
    """
       Add a new product to the database.

       This endpoint allows the creation of a new product with details
       :param product_data: The data required to create a new product.
       :type product_data: ProductCreateSchema
       :param db: The SQLAlchemy async database session (provided via dependency injection).
       :type db: AsyncSession

       :return: The created product with all details.
       :rtype: ProductDetailSchema

       :raises HTTPException:
           - 400 if input data is invalid (e.g., violating a constraint).
       """

    category_stmt = select(CategoryModel).where(CategoryModel.id == product_data.category_id)
    category_result = await db.execute(category_stmt)
    category = category_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")

    existing_stmt = select(ProductModel).where(ProductModel.name == product_data.name)
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Product with this name already exists.")

    try:
        product = ProductModel(
            name=product_data.name,
            description=product_data.description,
            price=product_data.price,
            stock=product_data.stock,
            category_id=product_data.category_id,
            image_url=product_data.image_url,
        )
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
    summary="Update an existing product",
    description=(
            "<h3>This endpoint allows admins to update an existing product in the database.</h3>"
    ),
    responses={
        200: {"description": "Product updated successfully."},
        400: {"description": "Invalid input or update data."},
        404: {"description": "Product or category not found."},
    },
    status_code=200
)
async def update_product(
        product_id: int,
        product_data: ProductUpdateSchema,
        db: AsyncSession = Depends(get_postgresql_db),
) -> ProductDetailSchema:
    """
    Updates an existing product in the database by its ID.

    :param product_id: ID of the product to update.
    :type product_id: int
    :param product_data: Data to update the product (partial or full).
    :type product_data: ProductUpdateSchema
    :param db: Asynchronous SQLAlchemy database session.
    :type db: AsyncSession
    :return: The updated product with all the details.
    :rtype: ProductDetailSchema
    :raises HTTPException:
        - 400 if the input data is incorrect (for example, violates restrictions)
        - 404 if the product or category is not found.
    """

    product_stmt = select(ProductModel).where(ProductModel.id == product_id)
    product_result = await db.execute(product_stmt)
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    if product_data.category_id is not None:
        category_stmt = select(CategoryModel).where(CategoryModel.id == product_data.category_id)
        category_result = await db.execute(category_stmt)
        category = category_result.scalar_one_or_none()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found.")

    if product_data.name is not None and product_data.name != product.name:
        existing_stmt = select(ProductModel).where(ProductModel.name == product_data.name)
        existing_result = await db.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Product with this name already exists.")
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
    summary="Delete a product",
    description=(
            "<h3>This endpoint allows to delete a product from the database.</h3>"
    ),
    responses={
        204: {"description": "Product deleted successfully."},
        403: {"description": "Admin access required."},
        404: {"description": "Product not found."},
    },
    status_code=204
)
async def delete_product(
        product_id: int,
        db: AsyncSession = Depends(get_postgresql_db),
):
    """
    Deletes a product from the database by its ID.

    :param product_id: ID of the product to be deleted.
    :type product_id: int
    :param db: Asynchronous SQLAlchemy database session.
    :type db: AsyncSession
    :return: Nothing is returned (204 No Content).
    :rtype: None
    :raises HTTPException:
        - 400 if the product cannot be uninstalled due to dependencies
        - 404 if the product was not found.
    """
    product_stmt = select(ProductModel).where(ProductModel.id == product_id)
    product_result = await db.execute(product_stmt)
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    await db.delete(product)
    await db.commit()
    return {"detail": "Movie deleted successfully."}


@router.get(
    "/category/",
    response_model=CategoryResponseSchema,
    summary="Get a paginated list of category",
    responses={
        404: {
            "description": "No product found.",
        },
    },
)
async def get_category_list(
        page: int = Query(1, ge=1, description="Page number (1-based index)"),
        per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
        db: AsyncSession = Depends(get_postgresql_db),
):
    """
    Fetch a paginated list of category from the database (asynchronously).

    This function retrieves a paginated list of category, allowing the client to specify
    the page number and the number of items per page. It calculates the total pages
    and provides links to the previous and next pages when applicable.

    :param page: The page number to retrieve (1-based index, must be >= 1).
    :type page: int
    :param per_page: The number of items to display per page (must be between 1 and 20).
    :type per_page: int
    :param db: The async SQLAlchemy database session (provided via dependency injection).
    :type db: AsyncSession

    :return: A response containing the paginated list of category and metadata.
    :rtype: CategoryResponseSchema

    :raises HTTPException: Raises a 404 error if no products are found for the requested page.
    """
    offset = (page - 1) * per_page

    count_stms = select(func.count(CategoryModel.id))
    result_count = await db.execute(count_stms)
    total_items = result_count.scalar() or 0
    if not total_items:
        raise HTTPException(status_code=404, detail="No category found.")

    stmt = select(CategoryModel)

    stmt = stmt.offset(offset).limit(per_page)
    result_category = await db.execute(stmt)
    category = result_category.scalars().all()

    if not category:
        raise HTTPException(status_code=404, detail="No category found.")

    category_list = [CategoryListSchema.model_validate(categories) for categories in category]

    total_pages = (total_items + per_page - 1) // per_page

    return CategoryResponseSchema(
        category=category_list,
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