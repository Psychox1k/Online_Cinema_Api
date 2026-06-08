import pytest
from fastapi import status

# ==============================================================================
# CREATE (POST) TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_create_genre_success_as_admin(admin_client):
    """
    Test that an admin user can successfully create a new genre.
    :param admin_client:
    :return:
    """
    payload = {"name": "Horror"}

    response = await admin_client.post("genres/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["name"] == "Horror"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_genre_forbidden_for_user(auth_client):
    """
    Test that a regular authenticated user cannot
    create a genre (403 Forbidden).
    :param auth_client:
    :return:
    """
    payload = {"name": "Thriller"}
    response = await auth_client.post("genres/", json=payload)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_genre_conflict(admin_client):
    """
    Test that creating a genre with an already existing
    name returns a 409 Conflict.
    :param admin_client:
    :return:
    """
    payload = {"name": "Comedy"}

    await admin_client.post("genres/", json=payload)

    response = await admin_client.post("genres/", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Genre already exists."


# ==============================================================================
# READ (GET) TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_get_all_genres_success(admin_client, client):
    """
    Test retrieving a list of all genres. Available to anonymous users.
    :param admin_client:
    :param client:
    :return:
    """
    await admin_client.post("genres/", json={"name": "Drama"})
    await admin_client.post("genres/", json={"name": "Fantasy"})
    await admin_client.post("genres/", json={"name": "Action"})

    response = await client.get("genres/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    assert any(genre["name"] == "Fantasy" for genre in data)


@pytest.mark.asyncio
async def test_get_genre_by_id_success(admin_client, client):
    """
    Test retrieving a specific genre by its ID.
    :param admin_client:
    :param client:
    :return:
    """
    create_response = await admin_client.post("genres/", json={"name": "Sci-Fi"})
    genre_id = create_response.json()["id"]

    # Action
    response = await client.get(f"genres/{genre_id}/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == genre_id
    assert data["name"] == "Sci-Fi"


@pytest.mark.asyncio
async def test_get_genre_by_id_not_found(client):
    """
    Test retrieving a non-existent genre returns a 404 Not Found.
    :param client:
    :return:
    """
    response = await client.get("genres/99999/")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Genre not found."


# ==============================================================================
# UPDATE (PATCH) TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_update_genre_success(admin_client):
    """
    Test that an admin can successfully update an existing genre's name.
    :param admin_client:
    :return:
    """
    create_response = await admin_client.post("genres/", json={"name": "Old Genre"})
    genre_id = create_response.json()["id"]

    update_payload = {"name": "New Genre"}
    response = await admin_client.patch(f"genres/{genre_id}/", json=update_payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "New Genre"


@pytest.mark.asyncio
async def test_update_genre_forbidden_for_user(auth_client, create_test_genre):
    """
    Test that a regular user cannot update a genre.
    Uses factory to prevent client fixture clashing.
    :param auth_client:
    :param create_test_genre:
    :return:
    """
    genre = await create_test_genre(name="Documentary")

    response = await auth_client.patch(
        f"genres/{genre.id}/", json={"name": "Hacked Genre"}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# DELETE TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_delete_genre_success(admin_client, client):
    """
    Test that an admin can successfully delete a genre.
    :param admin_client:
    :param client:
    :return:
    """
    create_response = await admin_client.post("genres/", json={"name": "To Be Deleted"})
    genre_id = create_response.json()["id"]

    delete_response = await admin_client.delete(f"genres/{genre_id}/")
    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json()["message"] == "Genre successfully deleted."

    get_response = await client.get(f"genres/{genre_id}/")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_genre_forbidden_for_user(auth_client, create_test_genre):
    """
    Test that a regular user cannot delete a genre.
    Uses factory to prevent client fixture clashing.
    :param auth_client:
    :param create_test_genre:
    :return:
    """
    genre = await create_test_genre(name="Safe Genre")

    response = await auth_client.delete(f"genres/{genre.id}/")

    assert response.status_code == status.HTTP_403_FORBIDDEN
