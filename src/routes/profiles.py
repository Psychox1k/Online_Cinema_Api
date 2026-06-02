import asyncio
from datetime import date

from fastapi import (
    APIRouter,
    status,
    Depends,
    HTTPException,
    Form,
    File,
    UploadFile
)
from sqlalchemy import select, cast
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_user, get_s3_storage_client
from database import get_db, UserModel, UserProfileModel
from exceptions import S3FileUploadError
from schemas.profiles import ProfileResponseSchema
from storages import S3StorageInterface

router = APIRouter()

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ProfileResponseSchema,
    summary="Create user profile",
    description="Create a new profile for the authenticated user.",
    responses={
        400: {
            "description": "Bad Request - User already has a profile.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User already has a profile."
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Invalid or missing "
                           "authentication token.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid or expired token."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while"
                           " creating the profile.",
            "content": {
                "application/json": {
                    "examples": {
                        "s3_error": {
                            "summary": "S3 Upload Error",
                            "value": {
                                "detail": "Failed to upload avatar. Please"
                                          " try again later."
                            }
                        },
                        "db_error": {
                            "summary": "Database Error",
                            "value": {
                                "detail": "An error occurred while creating"
                                          " profile."
                            }
                        }
                    }
                }
            },
        },
    },
)
async def create_profile(
        first_name: str = Form(...),
        last_name: str = Form(...),
        gender: str = Form(...),
        date_of_birth: date = Form(...),
        info: str = Form(...),
        avatar: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        s3_client: S3StorageInterface = Depends(get_s3_storage_client),
        current_user: UserModel = Depends(get_current_user)
) -> ProfileResponseSchema:
    try:
        stmt = select(UserProfileModel).filter_by(user_id=current_user.id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while checking existing profiles."
        )

    if profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a profile."
        )

    avatar_bytes = await avatar.read()
    avatar_key = f"avatars/{current_user.id}_{avatar.filename}"

    try:
        await s3_client.upload_file(
            file_name=avatar_key,
            file_data=avatar_bytes
        )
    except S3FileUploadError as e:
        print(f"Error uploading avatar to S3: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar. Please try again later."
        )

    new_profile = UserProfileModel(
        user_id=current_user.id,
        first_name=first_name,
        last_name=last_name,
        gender=gender,
        date_of_birth=date_of_birth,
        info=info,
        avatar=avatar_key
    )
    try:
        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating profile."
        )

    avatar_url = await s3_client.get_file_url(new_profile.avatar)

    return ProfileResponseSchema(
        id=new_profile.id,
        user_id=current_user.id,
        first_name=first_name,
        last_name=last_name,
        gender=gender,
        date_of_birth=date_of_birth,
        info=info,
        avatar=avatar_url
    )




@router.get(
    "/{profile_id}/",
    status_code=status.HTTP_200_OK,
    response_model=ProfileResponseSchema,
    summary="Get profile by ID",
    description="Retrieve a user profile by its ID.",
    responses={
        404: {
            "description": "Not Found - Profile with the given ID does not exist.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Profile with id 1 was not found."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while fetching the profile."
                    }
                }
            }
        }
    },
)
async def get_profile_by_id(
        profile_id: int,
        db: AsyncSession = Depends(get_db),
        s3_client: S3StorageInterface = Depends(get_s3_storage_client)
):
    try:
        stmt = select(UserProfileModel).where(UserProfileModel.id == profile_id)
        result = await db.execute(stmt)
        db_profile = result.scalar_one_or_none()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the profile."
        )

    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with id {profile_id} was not found."
        )

    avatar_url = await s3_client.get_file_url(db_profile.avatar)
    return ProfileResponseSchema(
        id=db_profile.id,
        user_id=db_profile.user_id,
        first_name=db_profile.first_name,
        last_name=db_profile.last_name,
        gender=db_profile.gender,
        date_of_birth=db_profile.date_of_birth,
        info=db_profile.info,
        avatar=avatar_url
    )


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=list[ProfileResponseSchema],
    summary="Get all profiles",
    description="Retrieve a list of all user profiles.",
    responses={
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while fetching profiles."
                    }
                }
            }
        }
    },
)
async def get_all_profiles(
    db: AsyncSession = Depends(get_db),
    s3_client: S3StorageInterface = Depends(get_s3_storage_client)
):
    try:
        stmt = select(UserProfileModel)
        result = await db.execute(stmt)
        db_profiles = result.scalars().all()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching profiles."
        )
    tasks = [s3_client.get_file_url(profile.avatar) for profile in db_profiles]
    avatar_urls = await asyncio.gather(*tasks)

    profiles = []
    for profile in db_profiles:
        avatar_url = await s3_client.get_file_url(profile.avatar)
        profiles.append(ProfileResponseSchema(
            id=profile.id,
            user_id=profile.user_id,
            first_name=profile.first_name,
            last_name=profile.last_name,
            gender=profile.gender,
            date_of_birth=profile.date_of_birth,
            info=profile.info,
            avatar=avatar_url
        ))

    return profiles