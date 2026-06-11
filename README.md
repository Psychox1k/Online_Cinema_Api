# 🎬 Online Cinema API

![Python](https://img.shields.io/badge/Python-3.13-blue.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-green.svg?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1.svg?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D.svg?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED.svg?logo=docker&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-373737.svg?logo=celery&logoColor=white)
![S3 Storage](https://img.shields.io/badge/S3_Storage-569A31.svg?logo=amazons3&logoColor=white)
![Mailhog](https://img.shields.io/badge/Mailhog-FF5733.svg?logo=privatepackagerepository&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF.svg?logo=githubactions&logoColor=white)

A robust RESTful API for a digital movie catalog. This service allows users to browse movies, manage their favorite lists, and securely process purchases. It also includes an admin interface for catalog management.

---
## 📌 Table of Contents

* [✨ Features (Deep Dive)](#-features-deep-dive)
* [🛠️ Tech Stack](#-tech-stack)
* [📂 Project Structure](#-project-structure)
* [🚀 Quick Start (Local Development)](#-quick-start-local-development)
* [🐳 Running with Docker](#-running-with-docker)
* [📖 API Documentation](#-api-documentation)
* [🧪 Testing](#-testing)
* [👨‍💻 About the Author](#-about-the-author)
* [📄 License](#-license)

---

## ✨ Features (Deep Dive)

* **🔐 Advanced Authentication Flow**
  * Secure user registration, account activation, and password reset workflows.
  * Role-Based Access Control (RBAC) with predefined user groups (Admin, Moderator, User).
  * Stateless session management utilizing JWT (Access and Refresh token rotation policy).
  * Password security powered by modern hashing algorithms.

* **🎬 Rich Movie Catalog System**
  * Comprehensive management of movies, genres, directors, and cast members.
  * Optimized asynchronous database querying featuring filtering, sorting, and pagination mechanisms.
  * Dynamic user interactions including movie ratings, custom reviews, and comment moderation controls.

* **🛒 Purchasing & Favorites Journey**
  * Fully functional shopping cart workflow allowing real-time items management.
  * Secure checkout lifecycle producing immutable orders and tracking purchase histories.
  * Global user Favorites list with quick toggle actions.

* **⚙️ Distributed Task Queue & Notifications**
  * Offloaded heavy operations (system emails, account activations) executed asynchronously via **Celery**.
  * Scheduled event tracking and periodic management updates automated through **Celery Beat**.
  * Local SMTP debugging and isolation provided by **Mailhog**.

* **📦 Enterprise-Grade Infrastructure**
  * Storage solution integrating **MinIO / S3-compatible API** for media assets.
  * Database schema evolutions explicitly mapped and tracked using **Alembic** migrations.
  * Production ready container multi-orchestration using **Docker Compose**.
  * Strict formatting and linting rules enforced dynamically via **Black** and **Flake8**.

---

## 🛠️ Tech Stack

* **Framework:** FastAPI
* **Database:** PostgreSQL (asyncpg) + SQLAlchemy
* **Caching/Brokers:** Redis
* **Testing:** Pytest (Unit, Integration, and E2E with Asyncio)
* **Containerization:** Docker & Docker Compose
* **Package Management:** Poetry
* **GitHub Actions** CI/CD Pipelines

## 📖 API Documentation

Once the server is running, you can explore and interact with the API endpoints using the following built-in documentation interfaces:

* **Interactive Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) — Best for testing endpoints, executing mock requests, and observing live server responses.
* **ReDoc (Three-Panel View):** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) — Clean, human-readable layout optimized for deep schema analysis and tracking technical specifications.
* **Raw OpenAPI Specification:** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json) — The auto-generated JSON matrix outlining the entire API architecture.

---


## 📂 Project Structure

```
.
├── Dockerfile
├── README.md
├── alembic
│   ├── README
│   ├── env.py
│   ├── script.py.mako
│   └── versions
│       ├── 075e386d6de6_add_user_id_to_comment_likes.py
│       ├── 0c04c8a6a6f8_add_carts_and_notifications.py
│       ├── 668062c359b9_add_movies_models_and_update_user_model.py
│       ├── 7e3f0aeee20f_add_orders_and_order_items_tables.py
│       ├── 993597da6296_initial_accounts_models.py
│       └── d2433b3bc450_seed_user_groups.py
├── alembic.ini
├── docker-compose-e2e.yml
├── docker-compose.yml
├── poetry.lock
├── pyproject.toml
└── src
    ├── __init__.py
    ├── celery_app
    │   ├── __init__.py
    │   ├── beat.py
    │   ├── tasks.py
    │   └── worker.py
    ├── config
    │   ├── __init__.py
    │   ├── dependencies.py
    │   └── settings.py
    ├── database
    │   ├── __init__.py
    │   ├── models
    │   │   ├── __init__.py
    │   │   ├── accounts.py
    │   │   ├── base.py
    │   │   ├── carts.py
    │   │   ├── movies.py
    │   │   ├── notifications.py
    │   │   └── orders.py
    │   ├── session.py
    │   └── validators
    │       ├── __init__.py
    │       └── accounts.py
    ├── exceptions
    │   ├── __init__.py
    │   ├── email.py
    │   ├── security.py
    │   └── storage.py
    ├── main.py
    ├── notifications
    │   ├── __init__.py
    │   ├── emails.py
    │   ├── interfaces.py
    │   └── templates
    │       ├── activation_complete.html
    │       ├── activation_request.html
    │       ├── password_reset_complete.html
    │       └── password_reset_request.html
    ├── routes
    │   ├── __init__.py
    │   ├── accounts.py
    │   ├── carts.py
    │   ├── directors.py
    │   ├── genres.py
    │   ├── movies.py
    │   ├── notifications.py
    │   ├── orders.py
    │   ├── profiles.py
    │   └── stars.py
    ├── schemas
    │   ├── __init__.py
    │   ├── accounts.py
    │   ├── carts.py
    │   ├── movies.py
    │   ├── notifications.py
    │   ├── orders.py
    │   └── profiles.py
    ├── security
    │   ├── __init__.py
    │   ├── jwt_interfaces.py
    │   ├── passwords.py
    │   ├── token_manager.py
    │   └── utils.py
    ├── seed.py
    ├── storages
    │   ├── __init__.py
    │   ├── interfaces.py
    │   └── s3client.py
    ├── tests
    │   ├── __init__.py
    │   ├── conftest.py
    │   ├── e2e
    │   │   ├── __init__.py
    │   │   ├── test_e2e_auth_flow_register_and_login.py
    │   │   ├── test_edge_cases.py
    │   │   └── test_user_journeys.py
    │   ├── integration
    │   │   ├── __init__.py
    │   │   ├── test_accounts.py
    │   │   ├── test_carts.py
    │   │   ├── test_comments.py
    │   │   ├── test_directors.py
    │   │   ├── test_genres.py
    │   │   ├── test_movie_interactions.py
    │   │   ├── test_movies.py
    │   │   ├── test_notifications.py
    │   │   ├── test_orders.py
    │   │   ├── test_profiles.py
    │   │   └── test_stars.py
    │   └── unit
    │       ├── __init__.py
    │       ├── test_jwt.py
    │       ├── test_schemas_accounts.py
    │       ├── test_schemas_movies.py
    │       └── test_validators_profiles.py
    └── validation
        ├── __init__.py
        ├── movies.py
        └── profile.py

21 directories, 99 files

```

## 🚀 Quick Start (Local Development)

### Prerequisites
Make sure you have [Python 3.13+](https://www.python.org/) and [Poetry](https://python-poetry.org/) installed on your machine.

### Installation & Setup

1. **Clone the repository:**
```bash
git clone [https://github.com/Psychox1k/Online_Cinema_Api.git](https://github.com/Psychox1k/Online_Cinema_Api.git)
cd Online_Cinema_Api
```
2. **Configure Environment Variables:**
Create a .env file in the root directory and copy the configuration:
```
# --- DATABASE SETTINGS ---
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_password
POSTGRES_HOST=db
POSTGRES_DB_PORT=5432
POSTGRES_DB=cinema_db

REDIS_HOST=redis
REDIS_PORT=6379
# --- APP SETTINGS ---
PROJECT_NAME="Online Cinema API"

# --- JWT SETTINGS ---
SECRET_KEY_ACCESS=your_secret_key_access
SECRET_KEY_REFRESH=your_secret_key_refresh

# --- EMAIL SETTINGS ---
EMAIL_HOST=mailhog
EMAIL_PORT=1025
EMAIL_HOST_USER=test@test.com
EMAIL_HOST_PASSWORD=password
EMAIL_USE_TLS=False

# --- S3 STORAGE ----
S3_STORAGE_HOST=minio
S3_STORAGE_PORT=9000
S3_STORAGE_ACCESS_KEY=minioadmin
S3_STORAGE_SECRET_KEY=minioadmin
S3_BUCKET_NAME=cinema-storage

# --- SWAGGER ----
SWAGGER_USER=user
SWAGGER_PASSWORD=your_super_secret_password
```
**3.Install dependencies:**

```
poetry install
```
**4.Run Database Migrations:**
```
poetry run alembic upgrade head
```

**5.Seed Initial Data:**
Populate the database with default groups, genres, and sample data:
```bash
poetry run python src/seed.py
```

**6.Start Background Services (Optional for Local Core Testing):**
If you want to run Celery workers locally without Docker:
```bash
# Run Celery Worker
poetry run celery -A src.celery_app.worker.celery worker --loglevel=info

# Run Celery Beat (for scheduled tasks)
poetry run celery -A src.celery_app.beat.celery_beat safe_beat
```
**7.Run the Application Server:**
Run the Application Server:
```bash
poetry run uvicorn src.main:app --reload
```


## 🐳 Running with Docker
To spin up the entire infrastructure (API, PostgreSQL, Redis, Celery, Mailhog, MinIO) in seconds with a single command:
```Bash
docker compose up --build -d
```
## 🧪 Testing
The project maintains a strict testing culture. To run the full test suite (Unit, Integration, and E2E) locally:
```bash
# Run tests via Poetry
poetry run pytest src/tests/

# Or run fully isolated E2E tests in Docker
docker compose -f docker-compose-e2e.yml up --build --abort-on-container-exit
```

## 👨‍💻 About the Author
* **Developer:** Kyrylo Zhyhariev
* **GitHub:** [@Psychox1k](https://github.com/Psychox1k)

## 📄 License
This project is licensed under the MIT License — feel free to modify, distribute, and integrate it into your workflows. See the root file definitions for metadata permissions.