 ## FastAPI-Store Project

Overview

FastAPI-Store is a web application built using FastAPI, designed to manage an online store with features for user registration, login, product management, shopping carts, and order processing. The project is structured with a modular design, utilizing Python, SQLAlchemy for database operations, and Pydantic for data validation.

## Project Structure
config/: Configuration files including authentication and settings.
database/: Database models and engine setup using SQLAlchemy.
routes/: API endpoints for account management, products, carts, and orders.
schemas/: Pydantic models for request and response validation.
security/: Authentication and token management utilities.
tests/: Unit and integration tests.

Additional files: .env, Dockerfile, poetry.lock, pyproject.toml, etc., for environment setup and dependency management.

## Features

User Management: Registration, login, password reset, and token refresh functionality.
Product Management: CRUD operations for products and categories (admin-only).
Shopping Cart: Add, update, and remove items; create and delete carts.
Order Processing: Create and delete orders based on cart contents.
Security: JWT-based authentication with role-based access control (admin/user).

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Grenders/FastApi-store.git

2. Create a virtual environment and activate it:
   ```bash
   poetry install

3. Create a .env file based on the .env.example file:
   ```bash
   cp .env.example .env
   Fill in the environment variables .env, example:
   SECRET_KEY=<your_unique_secret_key> # Generate with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   POSTGRES_HOST=db
   POSTGRES_DB=your_db_name
   POSTGRES_USER=your_user
   POSTGRES_PASSWORD=your_secure_password
   POSTGRES_PORT=5432


## The project is containerized using Docker and Docker Compose. It consists of Django and PostgreSQL services.

1. Install Docker and Docker Compose.
2. Create a .env file based on the .env.example file (see instructions above).
3. Start the project:
   ```bash
   docker-compose up --build
4. Swagger documentation is available at: http://localhost:8000/docs
5. To stop the containers:
    ```bash
   docker-compose down


# special command to create an admin user
   ```bash
   python src/create_superuser.py