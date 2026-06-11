import pytest
from fastapi import status

from database import CommentModel

# ==============================================================================
# CREATE (POST) TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_create_comment_success(auth_client, create_test_movie):
    """Test that an authenticated user can create a comment on a movie."""
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
    """Test that an anonymous user cannot create a comment."""
    movie = await create_test_movie(name="Anon Movie", year=2011)

    payload = {"text": "I shouldn't be able to post this."}
    response = await client.post(f"movies/{movie.id}/comments/", json=payload)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==============================================================================
# DELETE TESTS
# ==============================================================================
@pytest.mark.asyncio
async def test_user_cannot_delete_others_comment(
    auth_client,  # Уже авторизованный клиент (обычный юзер)
    create_test_movie,  # Фабрика фильмов
    create_test_admin,  # Фабрика для создания админа
    db_session,  # Сессия БД
):
    """Test that a regular user CANNOT delete someone else's comment."""

    movie = await create_test_movie(name="Another Movie", year=2013)

    admin_user = await create_test_admin(email="admin_comment_owner@gmail.com")

    other_comment = CommentModel(
        movie_id=movie.id, user_id=admin_user.id, text="This is admin's comment"
    )
    db_session.add(other_comment)
    await db_session.commit()
    await db_session.refresh(other_comment)

    delete_response = await auth_client.delete(
        f"movies/{movie.id}/comments/{other_comment.id}/"
    )

    assert delete_response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_admin_can_delete_others_comment(
    auth_client,
    admin_client,
    create_test_movie,
):
    """Test that an admin CAN delete a regular user's comment."""
    movie = await create_test_movie(name="Admin Delete Movie", year=2014)

    create_response = await auth_client.post(
        f"movies/{movie.id}/comments/",
        json={"text": "Regular user comment"},
    )
    comment_id = create_response.json()["id"]

    delete_response = await admin_client.delete(
        f"movies/{movie.id}/comments/{comment_id}/"
    )

    assert delete_response.status_code == status.HTTP_200_OK
    data = delete_response.json()
    assert data["message"] == "Comment was deleted successfully."
