import pytest
from fastapi import status

# ==============================================================================
# CREATE (POST) TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_add_movie_to_cart_success(auth_client, create_test_movie):
    """
    Test that a user can successfully add a movie to their cart.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Movie1", year=2002)

    response = await auth_client.post(f"carts/{movie.id}/")

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["items"][0]["id"] == movie.id
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_add_movie_to_cart_conflict(auth_client, create_test_movie):
    """
    Test that a user cannot add the same movie to their cart twice.
    :param auth_client:
    :param create_test_movie:
    :return:
    """

    movie = await create_test_movie(name="Inception", year=2010)

    await auth_client.post(f"carts/{movie.id}/")

    response = await auth_client.post(f"carts/{movie.id}/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "This movie is already in your cart."


@pytest.mark.asyncio
async def test_add_movie_to_cart_unauthorized(client, create_test_movie):
    """
    Test that an anonymous user cannot add a movie to the cart.
    :param client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Top Secret", year=2020)

    response = await client.post(f"carts/{movie.id}/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_add_nonexistent_movie_to_cart(auth_client):
    """
    Test adding a movie that does not exist.
    :param auth_client:
    :return:
    """
    response = await auth_client.post("carts/99999/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ==============================================================================
# READ (GET) TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_get_cart_items_success(auth_client, create_test_movie):
    """
    Test retrieving all items in the user's cart.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie1 = await create_test_movie(name="Movie One", year=2001)
    movie2 = await create_test_movie(name="Movie Two", year=2002)

    await auth_client.post(f"carts/{movie1.id}/")
    await auth_client.post(f"carts/{movie2.id}/")

    response = await auth_client.get("carts/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, dict)
    assert len(data["items"]) == 2

    movie_names = [item["movie"]["name"] for item in data["items"]]
    assert "Movie One" in movie_names
    assert "Movie Two" in movie_names


@pytest.mark.asyncio
async def test_get_empty_cart(auth_client):
    """
    Test retrieving a cart when it is empty.
    :param auth_client:
    :return:
    """
    response = await auth_client.get("carts/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, dict)
    assert len(data["items"]) == 0


# ==============================================================================
# DELETE TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_remove_movie_from_cart_success(auth_client, create_test_movie):
    """
    Test that a user can successfully remove a movie from their cart.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="To Be Removed", year=2005)
    await auth_client.post(f"carts/{movie.id}/")

    delete_response = await auth_client.delete(f"carts/{movie.id}/")

    assert delete_response.status_code == status.HTTP_200_OK
    data = delete_response.json()
    assert data["message"] == "Movie successfully removed from your cart."

    get_response = await auth_client.get("carts/")
    assert len(get_response.json()["items"]) == 0


@pytest.mark.asyncio
async def test_remove_movie_not_in_cart(auth_client, create_test_movie):
    """
    Test attempting to remove a movie that isn't in the user's cart.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Never Added", year=2006)

    response = await auth_client.delete(f"carts/{movie.id}/")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Item not found in cart."
