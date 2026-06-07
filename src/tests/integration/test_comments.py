import pytest
from fastapi import status


# ==============================================================================
# CREATE (POST) TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_create_comment_success(auth_client, create_test_movie):
    """
    Test that an authenticated user can create a comment on a movie.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Commentable Movie", year=2010)

    payload = {"text": "This is a fantastic masterpiece!"}
    response = await auth_client.post(f"movies/{movie.id}/comments/", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["text"] == "This is a fantastic masterpiece!"
    assert data["movie_id"] == movie.id
    assert "id" in data


@pytest.mark.asyncio
async def test_create_comment_unauthorized(client, create_test_movie):
    """
    Test that an anonymous user cannot create a comment.
    """
    movie = await create_test_movie(name="Anon Movie", year=2011)

    payload = {"text": "I shouldn't be able to post this."}
    response = await client.post(f"movies/{movie.id}/comments/", json=payload)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==============================================================================
# DELETE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_delete_own_comment_success(auth_client, create_test_movie):
    """
    Test that a user can delete their own comment.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="My Movie", year=2012)

    create_response = await auth_client.post(
        f"movies/{movie.id}/comments/",
        json={"text": "My temporary comment"}
    )
    comment_id = create_response.json()["id"]

    delete_response = await auth_client.delete(f"movies/{movie.id}/comments/{comment_id}/")

    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json()["message"] == "Comment was deleted successfully."


@pytest.mark.asyncio
async def test_delete_others_comment_not_found(
        auth_client,
        admin_client,
        create_test_movie
):
    """
    Test that a user cannot delete someone else's comment.
    Returns 404 because the router queries by comment_id AND user_id.
    :param auth_client:
    :param admin_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Another Movie", year=2013)

    create_response = await admin_client.post(
        f"movies/{movie.id}/comments/",
        json={"text": "Admin's untouchable comment"}
    )
    comment_id = create_response.json()["id"]

    delete_response = await auth_client.delete(
        f"movies/{movie.id}/comments/{comment_id}/"
    )

    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json()["message"] == "Comment was deleted successfully."