import pytest
from fastapi import status


# ==============================================================================
# CREATE (POST) TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_create_director_success_as_admin(admin_client):
    """
    Test that an admin user can successfully create a new director.
    :param admin_client:
    :return:
    """
    payload = {"name": "Christopher Nolan"}
    response = await admin_client.post("directors/", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Christopher Nolan"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_director_forbidden_for_user(auth_client):
    """
    Test that a regular authenticated user cannot create a director (403 Forbidden).
    :param auth_client:
    :return:
    """
    payload = {"name": "Steven Spielberg"}
    response = await auth_client.post("directors/", json=payload)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_director_conflict(admin_client):
    """
    Test that creating a director with an already existing name returns a 409 Conflict.
    :param admin_client:
    :return:
    """
    payload = {"name": "Denis Villeneuve"}

    # First creation should succeed
    await admin_client.post("directors/", json=payload)

    # Second creation with the same name should fail
    response = await admin_client.post("directors/", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Director already exists."


# ==============================================================================
# READ (GET) TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_get_all_directors_success(admin_client, client):
    """
    Test retrieving a list of all directors. Available to anonymous users.
    :param admin_client:
    :param client:
    :return:
    """
    await admin_client.post("directors/", json={"name": "Quentin Tarantino"})

    response = await client.get("directors/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check if the created director is in the returned list
    assert any(director["name"] == "Quentin Tarantino" for director in data)


@pytest.mark.asyncio
async def test_get_director_by_id_success(admin_client, client):
    """
    Test retrieving a specific director by their ID.
    :param admin_client:
    :param client:
    :return:
    """
    create_response = await admin_client.post("directors/", json={"name": "Guy Ritchie"})
    director_id = create_response.json()["id"]

    response = await client.get(f"directors/{director_id}/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == director_id
    assert data["name"] == "Guy Ritchie"


@pytest.mark.asyncio
async def test_get_director_by_id_not_found(client):
    """
    Test retrieving a non-existent director returns a 404 Not Found.
    :param client:
    :return:
    """
    response = await client.get("directors/99999/")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Director not found."


# ==============================================================================
# UPDATE (PATCH) TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_update_director_success(admin_client):
    """
    Test that an admin can successfully update an existing director's name.
    :param admin_client:
    :return:
    """
    create_response = await admin_client.post("directors/", json={"name": "Old Name"})
    director_id = create_response.json()["id"]

    update_payload = {"name": "New Updated Name"}
    response = await admin_client.patch(f"directors/{director_id}/", json=update_payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "New Updated Name"


@pytest.mark.asyncio
async def test_update_director_forbidden_for_user(create_test_director, auth_client):
    """
    Test that a regular user cannot update a director.
    :param create_test_director:
    :param auth_client:
    :return:
    """
    director = await create_test_director(name="Some Name")

    response = await auth_client.patch(
        f"directors/{director.id}/",
        json={"name": "Hacked Name"}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# DELETE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_delete_director_success(admin_client, client):
    """
    Test that an admin can successfully delete a director.
    :param admin_client:
    :param client:
    :return:
    """
    create_response = await admin_client.post("directors/", json={"name": "To Be Deleted"})
    director_id = create_response.json()["id"]

    delete_response = await admin_client.delete(f"directors/{director_id}/")
    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json()["message"] == "director successfully deleted."

    get_response = await client.get(f"directors/{director_id}/")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_director_forbidden_for_user(create_test_director, auth_client):
    """
    Test that a regular user cannot delete a director.
    :param create_test_director:
    :param auth_client:
    :return:
    """
    director = await create_test_director(name="James Cameron")

    response = await auth_client.delete(f"directors/{director.id}/")
    assert response.status_code == status.HTTP_403_FORBIDDEN
