import os
import uuid
from decimal import Decimal
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)

# ==============================================================================
# 1. ENVIRONMENT SETUP
# Set database environment variables BEFORE importing the app or settings
# ==============================================================================
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_DB"] = "cinema_db_test"
os.environ["DATABASE_URL"] = ("postgresql+asyncpg://postgres"
                              ":postgres_password@localhost:5432/cinema_db_test")

# Project imports (must be after environment setup)
from config.settings import settings
from database import (
    Base, get_db,
    UserGroupEnum,
    UserGroupModel,
    UserModel,
    DirectorModel,
    StarModel,
    GenreModel,
    MovieModel,
    CertificationModel,
    CartModel,
    OrderModel,
    NotificationModel,
    UserProfileModel
)
from main import app
from notifications import EmailSenderInterface
from security.passwords import hash_password
from config.dependencies import (
    get_accounts_email_notificator, get_s3_storage_client, get_current_user
)

# Test database engine and session factory
test_engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# ==============================================================================
# 2. MOCKS & DUMMIES
# ==============================================================================
class DummyEmailSender(EmailSenderInterface):
    """
    Mock implementation of EmailSenderInterface.
    Prevents actual emails from being sent during the test suite execution.
    """
    async def send_activation_email(self, email: str, link: str): pass

    async def send_activation_complete_email(self, email: str, link: str): pass

    async def send_password_reset_email(self, email: str, link: str): pass

    async def send_password_reset_complete_email(self, email: str, link: str): pass


class DummyS3Client:
    """
    Mock implementation of S3StorageInterface.
    Prevents actual files from being uploaded to AWS S3 during testing,
    returning fake URLs instead.
    """
    async def upload_file(self, file_name: str, file_data: bytes): pass

    async def get_file_url(self, file_name: str) -> str:
        return f"http://fake-s3-storage.test/{file_name}"


# ==============================================================================
# 3. DATABASE PREPARATION & CLEANUP
# ==============================================================================
@pytest.fixture(scope="session", autouse=True)
async def prepare_database():
    """
    Create tables and initialize static required data (like UserGroup roles)
    once per entire test session.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        for group in UserGroupEnum:
            session.add(UserGroupModel(name=group))
        await session.commit()
    yield


@pytest.fixture(scope="function", autouse=True)
async def clean_database():
    """
    Clear all dynamic table data before each individual test.
    Ensures complete state isolation between tests so they don't affect each other.
    """
    async with TestingSessionLocal() as session:
        await session.execute(delete(MovieModel))
        await session.execute(delete(DirectorModel))
        await session.execute(delete(StarModel))
        await session.execute(delete(GenreModel))
        await session.execute(delete(CertificationModel))
        await session.execute(delete(CartModel))
        await session.execute(delete(OrderModel))
        await session.execute(delete(NotificationModel))
        await session.execute(delete(UserProfileModel))

        await session.commit()


# ==============================================================================
# 4. CORE FIXTURES (SESSION & CLIENT)
# ==============================================================================
@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a fresh, isolated asynchronous database session for a single test.
    """
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide a standard asynchronous HTTP client for interacting with the API.
    Overrides core application dependencies (Database, Email, S3) with
     test-safe mocks.
    """
    async def _override_get_db():
        yield db_session

    base_api_url = f"http://test{settings.API_PREFIX}/"

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_accounts_email_notificator] = lambda: DummyEmailSender()
    app.dependency_overrides[get_s3_storage_client] = lambda: DummyS3Client()

    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url=base_api_url
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ==============================================================================
# 5. DATA FACTORIES
# ==============================================================================
@pytest.fixture(scope="function")
async def create_test_user(db_session):
    """Database factory for generating a standard User record."""
    async def _create_user(email: str, is_active: bool = True):
        group_stmt = select(UserGroupModel).where(
            UserGroupModel.name == UserGroupEnum.USER
        )
        group_result = await db_session.execute(group_stmt)
        user_group = group_result.scalar_one()

        user = UserModel(
            email=email,
            _hashed_password=hash_password("Password1234@"),
            is_active=is_active,
            group_id=user_group.id
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        user.group = user_group
        return user

    return _create_user


@pytest.fixture(scope="function")
async def create_test_moderator(db_session):
    """Database factory for generating a Moderator record."""
    async def _create_moderator(email: str, is_active: bool = True):
        group_stmt = select(UserGroupModel).where(
            UserGroupModel.name == UserGroupEnum.MODERATOR
        )
        group_result = await db_session.execute(group_stmt)
        moderator_group = group_result.scalar_one()

        moderator = UserModel(
            email=email,
            _hashed_password=hash_password("AdminPassword1234@"),
            is_active=is_active,
            group_id=moderator_group.id
        )

        db_session.add(moderator)
        await db_session.commit()
        await db_session.refresh(moderator)
        moderator.group = moderator_group
        return moderator

    return _create_moderator


@pytest.fixture(scope="function")
async def create_test_admin(db_session):
    """Database factory for generating an Administrator record."""
    async def _create_admin(email: str, is_active: bool = True):
        group_stmt = select(UserGroupModel).where(
            UserGroupModel.name == UserGroupEnum.ADMIN
        )
        group_result = await db_session.execute(group_stmt)
        admin_group = group_result.scalar_one()

        admin = UserModel(
            email=email,
            _hashed_password=hash_password("AdminPassword1234@"),
            is_active=is_active,
            group_id=admin_group.id
        )

        db_session.add(admin)
        await db_session.commit()
        await db_session.refresh(admin)
        admin.group = admin_group
        return admin

    return _create_admin


@pytest.fixture(scope="function")
async def auth_client(client, create_test_user):
    """
    Provide an API client pre-authenticated as a regular user.
    Bypasses the login route by overriding the get_current_user dependency.
    """
    unique_email = f"user_{uuid.uuid4().hex[:8]}@gmail.com"
    user = await create_test_user(email=unique_email)
    app.dependency_overrides[get_current_user] = lambda: user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(scope="function")
async def moderator_client(client, create_test_moderator):
    """
    Provide an API client pre-authenticated as a moderator.
    Bypasses the login route by overriding the get_current_user dependency.
    """
    unique_email = f"moderator_{uuid.uuid4().hex[:8]}@gmail.com"
    moderator = await create_test_moderator(email=unique_email)
    app.dependency_overrides[get_current_user] = lambda: moderator
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(scope="function")
async def admin_client(client, create_test_admin):
    """
    Provide an API client pre-authenticated as an administrator.
    Bypasses the login route by overriding the get_current_user dependency.
    """
    unique_email = f"admin_{uuid.uuid4().hex[:8]}@gmail.com"
    admin = await create_test_admin(email=unique_email)
    app.dependency_overrides[get_current_user] = lambda: admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(scope="function")
async def create_test_director(db_session):
    """Database factory for creating a Director record."""
    async def _create_director(name: str = "James Cameron"):
        director = DirectorModel(name=name)
        db_session.add(director)
        await db_session.commit()
        await db_session.refresh(director)
        return director
    return _create_director


@pytest.fixture(scope="function")
async def create_test_certification(db_session):
    """Database factory for creating a Certification (age rating) record."""
    async def _create_certification(name: str = "PG-13"):
        certification = CertificationModel(name=name)
        db_session.add(certification)
        await db_session.commit()
        await db_session.refresh(certification)
        return certification
    return _create_certification


@pytest.fixture(scope="function")
async def create_test_star(db_session):
    """Database factory for creating a Star (actor) record."""
    async def _create_star(name: str = "Christian Bale"):
        star = StarModel(name=name)
        db_session.add(star)
        await db_session.commit()
        await db_session.refresh(star)
        return star
    return _create_star


@pytest.fixture(scope="function")
async def create_test_genre(db_session):
    """Database factory for creating a Genre record."""
    async def _create_genre(name: str = "Action"):
        genre = GenreModel(name=name)
        db_session.add(genre)
        await db_session.commit()
        await db_session.refresh(genre)
        return genre
    return _create_genre


@pytest.fixture(scope="function")
async def create_test_movie(
        db_session,
        create_test_director,
        create_test_genre,
        create_test_star,
        create_test_certification
):
    """
    Database factory for creating a fully populated Movie record.
    Automatically generates and links required related entities
    (Directors, Genres, Stars, Certifications) using unique identifiers to
    prevent database conflicts during concurrent testing.
    """
    async def _create_movie(
            name: str = "Interstellar",
            year: int = 2014,
            price: float = 14.99
    ):
        uid = uuid.uuid4().hex[:6]

        director = await create_test_director(name=f"Director {uid}")
        genre = await create_test_genre(name=f"Genre {uid}")
        star = await create_test_star(name=f"Star {uid}")
        certification = await create_test_certification(name=f"Cert {uid}")

        movie = MovieModel(
            name=name,
            description="Great film about space",
            year=year,
            time=169,
            imdb=8.6,
            votes=1500000,
            price=Decimal(str(price)),
            certification_id=certification.id,
            directors=[director],
            stars=[star],
            genres=[genre]
        )

        db_session.add(movie)
        await db_session.commit()
        await db_session.refresh(movie)
        return movie

    return _create_movie
