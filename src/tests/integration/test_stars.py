import pytest
from fastapi import status

# ==============================================================================
# CREATE (POST) TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_create_star_success_as_admin(admin_client):
    """
    Test that an admin user can successfully create a new star.
    :param admin_client:
    :return:
    """
    payload = {"name": "Christian Bale"}
    response = await admin_client.post("stars/", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Christian Bale"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_star_forbidden_for_user(auth_client):
    """
    Test that a regular authenticated user cannot
     create a star (403 Forbidden).
    :param auth_client:
    :return:
    """
    payload = {"name": "Brad Pitt"}
    response = await auth_client.post("stars/", json=payload)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_star_conflict(admin_client):
    """
    Test that creating a star with an already
    existing name returns a 409 Conflict.
    :param admin_client:
    :return:
    """
    payload = {"name": "Tom Hardy"}

    await admin_client.post("stars/", json=payload)

    response = await admin_client.post("stars/", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Star already exists."


# ==============================================================================
# READ (GET) TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_get_all_stars_success(admin_client, client):
    """
    Test retrieving a list of all stars. Available to anonymous users.
    :param admin_client:
    :param client:
    :return:
    """
    await admin_client.post("stars/", json={"name": "Leonardo DiCaprio"})

    response = await client.get("stars/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(star["name"] == "Leonardo DiCaprio" for star in data)


@pytest.mark.asyncio
async def test_get_star_by_id_success(admin_client, client):
    """
    Test retrieving a specific star by their ID.
    :param admin_client:
    :param client:
    :return:
    """

    create_response = await admin_client.post(
        "stars/", json={"name": "Matthew McConaughey"}
    )
    star_id = create_response.json()["id"]

    response = await client.get(f"stars/{star_id}/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == star_id
    assert data["name"] == "Matthew McConaughey"


@pytest.mark.asyncio
async def test_get_star_by_id_not_found(client):
    """
    Test retrieving a non-existent star returns a 404 Not Found.
    :param client:
    :return:
    """
    response = await client.get("stars/99999/")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Star not found."


# ==============================================================================
# UPDATE (PATCH) TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_update_star_success(admin_client):
    """
    Test that an admin can successfully update an existing star's name.
    :param admin_client:
    :return:
    """
    create_response = await admin_client.post("stars/", json={"name": "Old Star Name"})
    star_id = create_response.json()["id"]

    update_payload = {"name": "New Updated Star Name"}
    response = await admin_client.patch(f"stars/{star_id}/", json=update_payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "New Updated Star Name"


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_update_star_forbidden_for_user(auth_client, create_test_star):
    """
    Test that a regular user cannot update a star.
    :param auth_client:
    :param create_test_star:
    :return:
    """

    star = await create_test_star(name="Ryan Gosling")

    response = await auth_client.patch(
        f"stars/{star.id}/", json={"name": "Hacked Star Name"}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# DELETE TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_delete_star_success(admin_client, client):
    """
    Test that an admin can successfully delete a star.
    :param admin_client:
    :param client:
    :return:
    """
    create_response = await admin_client.post(
        "stars/", json={"name": "Star To Be Deleted"}
    )
    star_id = create_response.json()["id"]

    delete_response = await admin_client.delete(f"stars/{star_id}/")
    assert delete_response.status_code == status.HTTP_200_OK

    assert delete_response.json()["message"] == "Star successfully deleted."

    get_response = await client.get(f"stars/{star_id}/")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_star_forbidden_for_user(auth_client, create_test_star):
    """
    Test that a regular user cannot delete a star.
    :param auth_client:
    :param create_test_star:
    :return:
    """

    star = await create_test_star(name="Safe Star")

    response = await auth_client.delete(f"stars/{star.id}/")

    assert response.status_code == status.HTTP_403_FORBIDDEN
