import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_e2e_full_user_purchasing_journey(
    auth_client, admin_client, create_test_movie
):
    """
    E2E Scenario: A complete user journey from browsing the catalog
    to making a purchase and canceling the order.
    :param create_test_movie:
    :param auth_client:
    :param admin_client:
    :return:
    """
    # STEP 1: Admin prepares the catalog
    movie_name = "Cyberpunk 2077"
    await create_test_movie(name=movie_name, year=2020)

    # STEP 2: User browses the catalog
    catalog_response = await auth_client.get(f"movies/?search={movie_name}")
    assert catalog_response.status_code == status.HTTP_200_OK

    catalog_data = catalog_response.json()
    assert len(catalog_data["items"]) == 1

    found_movie_id = catalog_data["items"][0]["id"]
    movie_price = catalog_data["items"][0]["price"]

    # STEP 3: User likes the movie
    like_response = await auth_client.post(
        f"movies/{found_movie_id}/like/", json={"is_like": True}
    )
    assert like_response.status_code == status.HTTP_200_OK

    # STEP 4: User adds the movie to their cart
    cart_add_response = await auth_client.post(f"carts/{found_movie_id}/")
    assert cart_add_response.status_code == status.HTTP_201_CREATED

    # STEP 5: User verifies their cart
    cart_get_response = await auth_client.get("carts/")
    assert cart_get_response.status_code == status.HTTP_200_OK

    cart_items = cart_get_response.json()["items"]
    assert len(cart_items) == 1
    assert cart_items[0]["movie"]["id"] == found_movie_id

    # STEP 6: User creates an order (Checkout)
    order_create_response = await auth_client.post("orders/")
    assert order_create_response.status_code == status.HTTP_201_CREATED

    order_data = order_create_response.json()
    order_id = order_data["id"]
    assert float(order_data["total_amount"]) == float(movie_price)
    assert order_data["status"] == "pending"

    # STEP 7: Verify cart is empty after checkout
    cart_empty_response = await auth_client.get("carts/")
    assert len(cart_empty_response.json()["items"]) == 0

    # STEP 8: User cancels the order
    cancel_response = await auth_client.patch(f"orders/{order_id}/cancel/")
    assert cancel_response.status_code == status.HTTP_200_OK

    # STEP 9: Final check - order is canceled in history
    history_response = await auth_client.get(f"orders/{order_id}/")
    assert history_response.status_code == status.HTTP_200_OK
    assert history_response.json()["status"] == "canceled"
