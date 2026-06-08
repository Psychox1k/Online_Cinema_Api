import pytest
import uuid
from fastapi import status

from config.dependencies import get_current_user
from main import app


@pytest.mark.asyncio
async def test_movie_delete_creates_notification(
    moderator_client,
    client,
    auth_client,
    create_test_movie,
    create_test_admin,
    create_test_moderator,
):
    """
    Test that deleting a movie present in users' carts generates
    notifications for administrators and moderators.
    :param moderator_client:
    :param client:
    :param auth_client:
    :param create_test_movie:
    :param create_test_admin:
    :param create_test_moderator:
    :return:
    """
    movie = await create_test_movie(name="Doomed Movie", year=2024)
    await auth_client.post(f"carts/{movie.id}/")
    moder_email = f"dynamic_mod_{uuid.uuid4().hex[:4]}@cinema.com"
    moderator_user = await create_test_moderator(email=moder_email)

    admin_email = f"dynamic_admin_{uuid.uuid4().hex[:4]}@cinema.com"
    admin_user = await create_test_admin(email=admin_email)

    app.dependency_overrides[get_current_user] = lambda: admin_user

    delete_response = await client.delete(f"movies/{movie.id}/")
    assert delete_response.status_code == status.HTTP_200_OK

    app.dependency_overrides[get_current_user] = lambda: moderator_user

    response = await client.get("notifications/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    expected_message = (
        f"Admin {admin_user.email} deleted movie '{movie.name}'"
        f" (ID: {movie.id}),"
        f" which was present in 1 user carts."
    )

    assert data[0]["message"] == expected_message

    app.dependency_overrides.pop(get_current_user, None)
