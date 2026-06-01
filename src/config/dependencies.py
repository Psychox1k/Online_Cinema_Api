from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer
from fastapi import status, HTTPException, Depends
from sqlalchemy.orm import joinedload

from database import get_db, UserModel, UserGroupEnum, MovieModel
from database.models.carts import CartModel
from exceptions import BaseSecurityError
from notifications import EmailSender, EmailSenderInterface
from config.settings import Settings, settings
from security.jwt_interfaces import JWTAuthManagerInterface
from security.token_manager import JWTAuthManager
from storages import S3StorageInterface, S3StorageClient

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/accounts/login/")

def get_settings() -> Settings:
    return settings

def get_accounts_email_notificator(
    settings: Settings = Depends(get_settings)
) -> EmailSenderInterface:
    """
    Retrieve an instance of the EmailSenderInterface configured with the application settings.

    This function creates an EmailSender using the provided settings, which include details such as the email host,
    port, credentials, TLS usage, and the directory and filenames for email templates. This allows the application
    to send various email notifications (e.g., activation, password reset) as required.

    Args:
        settings (BaseAppSettings, optional): The application settings,
        provided via dependency injection from `get_settings`.

    Returns:
        EmailSenderInterface: An instance of EmailSender configured with the appropriate email settings.
    """
    return EmailSender(
        hostname=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        email=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
        template_dir=settings.PATH_TO_EMAIL_TEMPLATES_DIR,
        activation_email_template_name=settings.ACTIVATION_EMAIL_TEMPLATE_NAME,
        activation_complete_email_template_name=settings.ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME,
        password_email_template_name=settings.PASSWORD_RESET_TEMPLATE_NAME,
        password_complete_email_template_name=settings.PASSWORD_RESET_COMPLETE_TEMPLATE_NAME
    )

def get_jwt_auth_manager(settings: Settings = Depends(get_settings)) -> JWTAuthManagerInterface:
    """
    Create and return a JWT authentication manager instance.

    This function uses the provided application settings to instantiate a JWTAuthManager, which implements
    the JWTAuthManagerInterface. The manager is configured with secret keys for access and refresh tokens
    as well as the JWT signing algorithm specified in the settings.

    Args:
        settings (BaseAppSettings, optional): The application settings instance.
        Defaults to the output of get_settings().

    Returns:
        JWTAuthManagerInterface: An instance of JWTAuthManager configured with
        the appropriate secret keys and algorithm.
    """
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> UserModel:
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except BaseSecurityError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token."
        )

    stmt = select(UserModel).options(
        joinedload(UserModel.group)
    ).where(UserModel.id == user_id)

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found."
        )

    return user

async def get_current_moderator(
        current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    if not current_user.has_group(UserGroupEnum.MODERATOR) and \
        not current_user.has_group(UserGroupEnum.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only moderators can perform this action"
        )
    return current_user


async def get_current_admin(
    current_user:UserModel = Depends(get_current_user)
) -> UserModel:
    if not current_user.has_group(UserGroupEnum.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action"
        )
    return current_user

def get_s3_storage_client(
    settings: Settings = Depends(get_settings)
) -> S3StorageInterface:
    """
    Retrieve an instance of the S3StorageInterface configured with the application settings.

    This function instantiates an S3StorageClient using the provided settings, which include the S3 endpoint URL,
    access credentials, and the bucket name. The returned client can be used to interact with an S3-compatible
    storage service for file uploads and URL generation.

    Args:
        settings (BaseAppSettings, optional): The application settings,
        provided via dependency injection from `get_settings`.

    Returns:
        S3StorageInterface: An instance of S3StorageClient configured with the appropriate S3 storage settings.
    """
    return S3StorageClient(
        endpoint_url=settings.S3_STORAGE_ENDPOINT,
        access_key=settings.S3_STORAGE_ACCESS_KEY,
        secret_key=settings.S3_STORAGE_SECRET_KEY,
        bucket_name=settings.S3_BUCKET_NAME
    )

async def get_movie_or_404(
    movie_id: int,
    db: AsyncSession = Depends(get_db)
) -> MovieModel:
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )
    return movie


async def get_or_create_user_cart(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(CartModel).where(CartModel.user_id == current_user.id)
    result = await db.execute(stmt)
    cart = result.scalar_one_or_none()

    if not cart:
        cart = CartModel(user_id=current_user.id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)

    return cart
