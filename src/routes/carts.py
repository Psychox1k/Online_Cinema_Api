from fastapi import APIRouter, status, HTTPException
from fastapi.params import Depends
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.dependencies import (
    get_current_user,
    get_movie_or_404,
    get_or_create_user_cart,
    get_current_admin
)
from database import UserModel, get_db, MovieModel, OrderModel, OrderItemModel, OrderStatusEnum
from database.models.carts import CartModel, CartItemModel
from schemas import CartSchema, MessageResponseSchema

router = APIRouter()


@router.get(
    "/",
    response_model=CartSchema,
    status_code=status.HTTP_200_OK,
    summary="Get current user's cart",
    description="Retrieves the active shopping cart and all its items for"
                " the currently authenticated user. Calculates the total"
                " price automatically."
)
async def get_own_cart(
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        cart: CartModel = Depends(get_or_create_user_cart),
) -> CartSchema:
    stmt = select(CartItemModel).where(
        CartItemModel.cart_id == cart.id
    ).options(
            selectinload(CartItemModel.movie).selectinload(MovieModel.genres)
        )

    result = await db.execute(stmt)
    items = result.scalars().all()

    total_price = sum(item.movie.price for item in items)

    return CartSchema(
        id=cart.id,
        items=items,
        total_price=total_price
    )


@router.post(
    "/{movie_id}/",
    response_model=CartSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add movie to cart",
    description="Adds a specific movie to the user's shopping cart. Validates that the movie isn't already in the cart or purchased.",
    responses={
        400: {
            "description": "Bad Request - Movie is already in the cart, purchased, or pending.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "This movie is already in your cart."
                    }
                }
            }
        },
        404: {
            "description": "Not Found - Movie doesn't exist.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while adding the movie to your cart."
                    }
                }
            }
        }
    }
)
async def add_movie_to_cart(
        movie_id: int,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        movie: MovieModel = Depends(get_movie_or_404),
        cart: CartModel = Depends(get_or_create_user_cart),
) -> CartSchema:
    stmt = select(CartItemModel).where(
        CartItemModel.cart_id == cart.id,
        CartItemModel.movie_id == movie.id
    )
    result = await db.execute(stmt)
    existing_item = result.scalar_one_or_none()

    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This movie is already in your cart."
        )

    check_order_stmt = select(OrderModel).join(OrderItemModel).where(
        OrderModel.user_id == current_user.id,
        OrderItemModel.movie_id == movie_id,
        OrderModel.status.in_([OrderStatusEnum.PAID, OrderStatusEnum.PENDING])
    )
    order_result = await db.execute(check_order_stmt)
    already_ordered = order_result.scalars().first()

    if already_ordered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already purchased this movie or have a pending order for it."
        )


    try:
        new_item = CartItemModel(
            cart_id=cart.id,
            movie_id=movie_id
        )
        db.add(new_item)
        await db.commit()

        items_stmt = select(CartItemModel).where(
            CartItemModel.cart_id == cart.id
        ).options(selectinload(CartItemModel.movie).selectinload(MovieModel.genres))
        items_result = await db.execute(items_stmt)
        items = items_result.scalars().all()

        return CartSchema(
            id=cart.id,
            items=items,
            total_price=sum(item.movie.price for item in items)
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while adding the movie to your cart."
        )


@router.delete(
    "/{movie_id}/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Remove movie from cart",
    description="Removes a specific movie from the current user's shopping cart."
)
async def remove_movie_from_cart(
        movie_id: int,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        movie: MovieModel = Depends(get_movie_or_404),
        cart: CartModel = Depends(get_or_create_user_cart)
) -> MessageResponseSchema:
    stmt = select(CartItemModel).where(
        CartItemModel.movie_id == movie.id,
        CartItemModel.cart_id == cart.id
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with ID {movie_id} was not found in your cart."
        )

    try:
        await db.delete(item)
        await db.commit()
        return MessageResponseSchema(message="Movie successfully removed from your cart.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while removing the movie from your cart."
        )


@router.delete(
    "/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Empty cart",
    description="Removes all items from the current user's shopping cart."
)
async def empty_own_cart(
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        cart: CartModel = Depends(get_or_create_user_cart)
) -> MessageResponseSchema:
    try:
        stmt = delete(CartItemModel).where(CartItemModel.cart_id == cart.id)
        result = await db.execute(stmt)

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your cart is already empty."
            )

        await db.commit()
        return MessageResponseSchema(message="Your cart has been emptied successfully.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while emptying your cart."
        )


@router.get(
    "/user/{user_id}/",
    response_model=CartSchema,
    status_code=status.HTTP_200_OK,
    summary="Get user's cart by ID (Admin)",
    description="Retrieves the shopping cart of a specific user. Only accessible by administrators."
)
async def get_user_cart_by_id(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_admin)
) -> CartSchema:
    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    stmt = select(CartModel).where(CartModel.user_id == user_id)
    result = await db.execute(stmt)
    user_cart = result.scalar_one_or_none()

    if not user_cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user does not have an active cart."
        )

    stmt = select(CartItemModel).where(
        CartItemModel.cart_id == user_cart.id
    ).options(
            selectinload(CartItemModel.movie).selectinload(MovieModel.genres)
        )
    result = await db.execute(stmt)
    items = result.scalars().all()

    total_price = sum(item.movie.price for item in items)

    return CartSchema(
        id=user_cart.id,
        items=items,
        total_price=total_price
    )