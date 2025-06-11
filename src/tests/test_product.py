import pytest
from fastapi import status
from src.schemas.product import ProductResponseSchema
from src.database.models.product import ProductModel
from fastapi.security import HTTPAuthorizationCredentials

@pytest.mark.asyncio
async def test_get_product_list_success(client, sample_data, override_current_user):
    response = client.get("/products/?page=1&per_page=10")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    product_response = ProductResponseSchema(**data)

    assert len(product_response.products) == 10
    assert product_response.total_items == 24
    assert product_response.total_pages == 3
    assert product_response.next_page == "/products/?page=2&per_page=10"
    assert product_response.prev_page is None
    assert product_response.products[0].name == "PRODUCT 1"
    assert product_response.products[0].price == 10.99

@pytest.mark.asyncio
async def test_get_product_list_with_token(client, sample_data, auth_token):
    response = client.get("/products/?page=1&per_page=10", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    product_response = ProductResponseSchema(**data)

    assert len(product_response.products) == 10
    assert product_response.total_items == 24
    assert product_response.total_pages == 3
    assert product_response.products[0].name == "PRODUCT 1"  # Верхній регістр

@pytest.mark.asyncio
async def test_get_product_list_page_2(client, sample_data, override_current_user):
    response = client.get("/products/?page=2&per_page=10")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    product_response = ProductResponseSchema(**data)

    assert len(product_response.products) == 10
    assert product_response.products[0].name == "PRODUCT 11"  # Верхній регістр
    assert product_response.prev_page == "/products/?page=1&per_page=10"
    assert product_response.next_page == "/products/?page=3&per_page=10"

@pytest.mark.asyncio
async def test_get_product_list_empty(client, override_current_user):
    response = client.get("/products/?page=1&per_page=10")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "No products found."}

@pytest.mark.asyncio
async def test_get_product_list_invalid_page(client, sample_data, override_current_user):
    response = client.get("/products/?page=0&per_page=10")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

@pytest.mark.asyncio
async def test_get_product_list_invalid_per_page(client, sample_data, override_current_user):
    response = client.get("/products/?page=1&per_page=21")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

@pytest.mark.asyncio
async def test_get_product_list_unauthenticated(client, sample_data):
    response = client.get("/products/?page=1&per_page=10")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid authentication credentials"}

@pytest.mark.asyncio
async def test_get_product_list_invalid_token(client, sample_data):
    response = client.get("/products/?page=1&per_page=10", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Could not validate credentials"}