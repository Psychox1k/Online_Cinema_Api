import pytest
from fastapi import status
from starlette.status import HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_e2e_admin_deletes_movie_during_checkout(
        auth_client,
        admin_client,
        create_test_movie
):
    """
    E2E Edge Case: A user adds a movie to their cart.
    Before they can checkout, an admin deletes the movie from the catalog.
    The checkout process must handle this gracefully without a 500 error.
    :param auth_client:
    :param admin_client:
    :param create_test_movie:
    :return:
    """
    # STEP 1: Prepare the movie
    movie = await create_test_movie(name="Vanishing Movie")
    movie_id = movie.id

    # STEP 2: User adds the movie to their cart
    cart_add_response = await auth_client.post(f"carts/{movie_id}/")
    assert cart_add_response.status_code == status.HTTP_201_CREATED

    # STEP 3: Verify it's in the cart
    cart_get_response = await auth_client.get("carts/")
    assert len(cart_get_response.json()["items"]) == 1

    # STEP 4: Admin DELETES the movie from the system
    delete_response = await admin_client.delete(f"movies/{movie_id}/")
    assert delete_response.status_code == status.HTTP_200_OK

    # STEP 5: User attempts to checkout (create an order)
    order_create_response = await auth_client.post("orders/")


    assert order_create_response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR
    assert order_create_response.status_code == HTTP_400_BAD_REQUEST
