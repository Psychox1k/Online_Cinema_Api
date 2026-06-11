from datetime import datetime
from typing import Optional

from fastapi import APIRouter, status, HTTPException, Query
from fastapi.params import Depends
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.dependencies import (
    get_current_user,
    get_current_moderator,
    get_or_create_user_cart,
)
from database import (
    get_db,
    UserModel,
    OrderModel,
    CartModel,
    CartItemModel,
    OrderItemModel,
    OrderStatusEnum,
)
from schemas import OrderSchema, MessageResponseSchema

router = APIRouter()


@router.get(
    "/",
    response_model=list[OrderSchema],
    status_code=status.HTTP_200_OK,
    summary="Get user's orders",
    description="Retrieve a list of all orders placed by the currently"
    " authenticated user, sorted by the newest first.",
    responses={
        401: {
            "description": "Unauthorized - Missing or invalid token.",
            "content": {
                "application/json": {"example": {"detail": "Not authenticated"}}
            },
        },
        500: {
            "description": "Internal Server Error.",
            "content": {"application/json": {"example": {"detail": "Database error."}}},
        },
    },
)
async def get_own_orders(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    try:
        stmt = (
            select(OrderModel)
            .where(OrderModel.user_id == current_user.id)
            .options(selectinload(OrderModel.items).selectinload(OrderItemModel.movie))
            .order_by(OrderModel.created_at.desc())
        )

        result = await db.execute(stmt)
        return result.scalars().all()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching your orders.",
        )


@router.get(
    "/{order_id}/",
    response_model=OrderSchema,
    status_code=status.HTTP_200_OK,
    summary="Get order details",
    description="Retrieve detailed information about a specific order."
    " Users can only access their own orders.",
    responses={
        401: {
            "description": "Unauthorized - Missing or invalid token.",
            "content": {
                "application/json": {"example": {"detail": "Not authenticated"}}
            },
        },
        404: {
            "description": "Not Found - Order does not exist or does not"
            " belong to the user.",
            "content": {
                "application/json": {"example": {"detail": "Order was not found."}}
            },
        },
        500: {
            "description": "Internal Server Error.",
            "content": {"application/json": {"example": {"detail": "Database error."}}},
        },
    },
)
async def get_order_by_id(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    stmt = (
        select(OrderModel)
        .where(OrderModel.user_id == current_user.id, OrderModel.id == order_id)
        .options(selectinload(OrderModel.items).selectinload(OrderItemModel.movie))
    )
    result = await db.execute(stmt)

    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order was not found."
        )

    return order


@router.post(
    "/",
    response_model=OrderSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
    description="Create an order from the user's active shopping cart. "
    "Validates that the cart is not empty and that the movies"
    " haven't been purchased previously. Clears the cart upon"
    " success.",
    responses={
        400: {
            "description": "Bad Request - Cart is empty or movies already"
            " purchased/pending.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You cannot make an order" " with an empty cart."
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Missing or invalid token.",
            "content": {
                "application/json": {"example": {"detail": "Not authenticated"}}
            },
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred while creating the order."}
                }
            },
        },
    },
)
async def create_order(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    cart: CartModel = Depends(get_or_create_user_cart),
):
    stmt = (
        select(CartItemModel)
        .where(CartItemModel.cart_id == cart.id)
        .options(selectinload(CartItemModel.movie))
    )

    result = await db.execute(stmt)
    cart_items = result.scalars().all()

    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot make an order with an empty cart.",
        )

    movie_ids_in_cart = [item.movie.id for item in cart_items]

    check_stmt = (
        select(OrderItemModel.movie_id)
        .join(OrderModel)
        .where(
            OrderModel.user_id == current_user.id,
            OrderModel.status.in_([OrderStatusEnum.PENDING, OrderStatusEnum.PAID]),
            OrderItemModel.movie_id.in_(movie_ids_in_cart),
        )
    )
    already_ordered_result = await db.execute(check_stmt)
    already_ordered_movies = already_ordered_result.scalars().all()

    if already_ordered_movies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already purchased or have pending "
            f"orders for movies with IDs: {already_ordered_movies}",
        )

    total_amount = sum(item.movie.price for item in cart_items)

    try:
        order = OrderModel(
            user_id=current_user.id,
            total_amount=total_amount,
            status=OrderStatusEnum.PENDING,
        )
        db.add(order)
        await db.flush()

        for c_item in cart_items:
            order_item = OrderItemModel(
                order_id=order.id,
                movie_id=c_item.movie.id,
                price_at_order=c_item.movie.price,
            )
            db.add(order_item)

        delete_stmt = delete(CartItemModel).where(CartItemModel.cart_id == cart.id)
        await db.execute(delete_stmt)
        await db.commit()

        await db.refresh(order, ["items"])

        return await get_order_by_id(
            order_id=order.id, db=db, current_user=current_user
        )

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the order.",
        )


@router.patch(
    "/{order_id}/cancel/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Cancel order",
    description="Cancel a specific order. Only orders in 'pending' status"
    " can be canceled.",
    responses={
        400: {
            "description": "Bad Request - Order is not in pending status.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You cannot cancel an " "order with status 'paid'."
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Missing or invalid token.",
            "content": {
                "application/json": {"example": {"detail": "Not authenticated"}}
            },
        },
        404: {
            "description": "Not Found - Order does not exist or does not"
            " belong to the user.",
            "content": {
                "application/json": {"example": {"detail": "Order was not found."}}
            },
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while canceling" " the order."
                    }
                }
            },
        },
    },
)
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    stmt = select(OrderModel).where(
        OrderModel.user_id == current_user.id, OrderModel.id == order_id
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order was not found."
        )
    if order.status != OrderStatusEnum.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You cannot cancel an order with"
            f" status '{order.status.value}'.",
        )

    try:
        order.status = OrderStatusEnum.CANCELED
        await db.commit()
        return MessageResponseSchema(message="Order has been successfully canceled.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while canceling the order.",
        )


@router.get(
    "/all/",
    response_model=list[OrderSchema],
    status_code=status.HTTP_200_OK,
    summary="Get all orders (Admin/Moderator)",
    description="Retrieve all orders in the system with optional filtering by"
    " user ID, exact status, and date range.",
    responses={
        401: {
            "description": "Unauthorized - Missing or invalid token.",
            "content": {
                "application/json": {"example": {"detail": "Not authenticated"}}
            },
        },
        403: {
            "description": "Forbidden - Insufficient permissions.",
            "content": {
                "application/json": {
                    "example": {"detail": "Only moderators can perform this action."}
                }
            },
        },
        500: {
            "description": "Internal Server Error.",
            "content": {"application/json": {"example": {"detail": "Database error."}}},
        },
    },
)
async def get_all_orders_for_admin(
    user_id: int | None = Query(default=None, description="Filter by User ID"),
    order_status: OrderStatusEnum | None = Query(
        default=None, description="Filter by order status"
    ),
    date_from: Optional[datetime] = Query(
        default=None, description="Start date (e.g., 2024-01-01T00:00:00)"
    ),
    date_to: Optional[datetime] = Query(
        default=None, description="End date (e.g., 2024-12-31T23:59:59)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_moderator),
):
    try:
        stmt = select(OrderModel).options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.movie)
        )

        if user_id:
            stmt = stmt.where(OrderModel.user_id == user_id)

        if order_status:
            stmt = stmt.where(OrderModel.status == order_status)

        if date_from:
            stmt = stmt.where(OrderModel.created_at >= date_from)

        if date_to:
            stmt = stmt.where(OrderModel.created_at <= date_to)

        stmt = stmt.order_by(OrderModel.created_at.desc())
        result = await db.execute(stmt)

        orders = result.scalars().all()

        return orders
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching orders.",
        )
