import pytest
from fastapi import status

# ==============================================================================
# FAVORITES TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_add_movie_to_favorites_success(auth_client, create_test_movie):
    """
    Test that a user can add a movie to their favorites.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Nice movie", year=2014)

    response = await auth_client.post(f"movies/{movie.id}/favorites/")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["message"] == ("Movie added to favorites" " successfully.")


@pytest.mark.asyncio
async def test_add_movie_to_favorites_unauthorized(client, create_test_movie):
    """
    Test that an unauthorized user can not add a movie to their favorites.
    :param client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Nice movie", year=2014)

    response = await client.post(f"movies/{movie.id}/favorites/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_add_movie_to_favorites_conflict(auth_client, create_test_movie):
    """
    Test that adding already favorited movie returns a 400 error.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Already Favorite", year=2021)

    # First addition
    await auth_client.post(f"movies/{movie.id}/favorites/")

    # Second addition attempt
    response = await auth_client.post(f"movies/{movie.id}/favorites/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Movie has already in your favorites."


@pytest.mark.asyncio
async def test_remove_movie_from_favorites_success(auth_client, create_test_movie):
    """
    Test that a user can remove a movie from their favorites.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="To Unfavorite", year=2022)

    await auth_client.post(f"movies/{movie.id}/favorites/")

    response = await auth_client.delete(f"movies/{movie.id}/favorites/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == (
        "Movie removed from favorites" " successfully."
    )


# ==============================================================================
# LIKES TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_like_movie_success(auth_client, create_test_movie):
    """
    Test that a user can like a movie.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Liked Movie", year=2023)

    payload = {"is_like": True}
    response = await auth_client.post(f"movies/{movie.id}/like/", json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Movie liked successfully."


@pytest.mark.asyncio
async def test_update_like_to_dislike(auth_client, create_test_movie):
    """
    Test that a user can change their vote from like to dislike.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Disliked Movie", year=2024)

    await auth_client.post(f"movies/{movie.id}/like/", json={"is_like": True})

    response = await auth_client.post(
        f"movies/{movie.id}/like/", json={"is_like": False}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Movie updated successfully."


@pytest.mark.asyncio
async def test_remove_like_success(auth_client, create_test_movie):
    """
    Test that a user can remove their like entirely.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Neutral Movie", year=2025)

    await auth_client.post(f"movies/{movie.id}/like/", json={"is_like": True})

    response = await auth_client.delete(f"movies/{movie.id}/like/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Like removed successfully."


# ==============================================================================
# RATING TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_rate_movie_success(auth_client, create_test_movie):
    """
    Test that a user can rate a movie from 1 to 10.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Rated Movie", year=2026)

    payload = {"rating": 8}
    response = await auth_client.post(f"movies/{movie.id}/rate/", json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Movie rated 8 successfully."


async def test_rate_movie_validation_error(auth_client, create_test_movie):
    """
    Test that a rating outside 1-10 returns a 422 Unprocessable Entity.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Invalid Rate Movie", year=2026)

    payload = {"rating": 15}
    response = await auth_client.post(f"movies/{movie.id}/rate/", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
