import pytest
from fastapi import status

from config.dependencies import get_current_user
from main import app

# ==============================================================================
# CREATE ORDER (CHECKOUT) TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_create_order_success(auth_client, create_test_movie):
    """
    Test that a user can successfully create an order from their cart.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie1 = await create_test_movie(name="Order Movie 1", year=2010)
    movie2 = await create_test_movie(name="Order Movie 2", year=2011)

    await auth_client.post(f"carts/{movie1.id}/")
    await auth_client.post(f"carts/{movie2.id}/")

    response = await auth_client.post("orders/")

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    assert float(data["total_amount"]) > 0
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_create_order_empty_cart_bad_request(auth_client):
    """
    Test that attempting to checkout with an empty cart returns a 400 error.
    :param auth_client:
    :return:
    """
    response = await auth_client.post("orders/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == (
        "You cannot make an order with an" " empty cart."
    )


# ==============================================================================
# READ (GET) ORDERS TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_get_user_orders_success(auth_client, create_test_movie):
    """
    Test that a user can retrieve their order history.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="History Movie", year=2011)
    await auth_client.post(f"carts/{movie.id}/")

    order_create_response = await auth_client.post("orders/")
    order_id = order_create_response.json()["id"]

    response = await auth_client.get(f"orders/{order_id}/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert isinstance(data, dict)
    assert data["id"] == order_id
    assert len(data["items"]) > 0
    assert float(data["total_amount"]) > 0


@pytest.mark.asyncio
async def test_get_order_by_id_success(auth_client, create_test_movie):
    """
    Test that a user can view details of a specific order.
    """
    movie = await create_test_movie(name="Specific Order Movie", year=2020)
    await auth_client.post(f"carts/{movie.id}/")

    order_create_response = await auth_client.post("orders/")
    order_id = order_create_response.json()["id"]

    response = await auth_client.get(f"orders/{order_id}/")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_get_others_order_forbidden(
    auth_client, create_test_user, create_test_movie
):
    """
    Test that a user cannot view someone else's
     order (404 Not Found or 403 Forbidden).
    :param auth_client:
    :param admin_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="User A Order Movie", year=2021)
    await auth_client.post(f"carts/{movie.id}/")
    order_resp = await auth_client.post("orders/")
    order_id = order_resp.json()["id"]

    user_b = await create_test_user(email="hacker_user@gmail.com")
    app.dependency_overrides[get_current_user] = lambda: user_b

    response = await auth_client.get(f"orders/{order_id}/")

    app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_cancel_order(auth_client, create_test_movie):
    """
    Test that a user can successfully cancel their pending order.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="User A Order Movie", year=2021)
    await auth_client.post(f"carts/{movie.id}/")
    order_resp = await auth_client.post("orders/")
    order_id = order_resp.json()["id"]

    response = await auth_client.patch(f"orders/{order_id}/cancel/")
    data = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert data["message"] == "Order has been successfully canceled."

    order_response = await auth_client.get(f"orders/{order_id}/")
    data = order_response.json()
    assert data["status"] == "canceled"
