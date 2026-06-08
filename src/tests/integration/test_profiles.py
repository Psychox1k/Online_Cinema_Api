import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_create_profile_success(auth_client):
    """
    Test successful profile creation via POST profiles/.
    :param auth_client:
    :return:
    """

    form_data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "man",
        "date_of_birth": "1995-05-15",
        "info": "Test information",
    }
    file_data = {"avatar": ("avatar.jpg", b"dummy_bytes", "image/jpeg")}

    response = await auth_client.post("profiles/", data=form_data, files=file_data)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["first_name"] == "John"
    assert data["gender"] == "man"
    assert "avatar" in data


@pytest.mark.asyncio
async def test_get_profile_by_id_success(auth_client):
    """
    Create a profile via API and retrieve it by ID.
    :param auth_client:
    :return:
    """
    form_data = {
        "first_name": "Jane",
        "last_name": "Smith",
        "gender": "woman",
        "date_of_birth": "1998-10-20",
        "info": "Engineer",
    }
    file_data = {"avatar": ("avatar.jpg", b"dummy_bytes", "image/jpeg")}

    create_response = await auth_client.post(
        "profiles/", data=form_data, files=file_data
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    profile_id = create_response.json()["id"]

    get_response = await auth_client.get(f"profiles/{profile_id}/")
    assert get_response.status_code == status.HTTP_200_OK

    data = get_response.json()
    assert data["id"] == profile_id
    assert data["first_name"] == "Jane"


@pytest.mark.asyncio
async def test_create_profile_invalid_gender_fails(auth_client):
    """
    Test invalid gender. Since Form() bypasses Pydantic, the DB catches it
    and triggers a 500 Internal Server Error in the current router logic.
    :param auth_client:
    :return:
    """
    form_data = {
        "first_name": "Alien",
        "last_name": "Predator",
        "gender": "invalid_gender",
        "date_of_birth": "1990-01-01",
        "info": "Valid info",
    }
    file_data = {"avatar": ("avatar.jpg", b"dummy_bytes", "image/jpeg")}

    response = await auth_client.post("profiles/", data=form_data, files=file_data)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_create_profile_duplicate_fails(auth_client):
    """
    Test that creating a second profile for the same user returns a 400 error.
    :param auth_client:
    :return:
    """
    form_data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "man",
        "date_of_birth": "1990-01-01",
        "info": "Info",
    }
    file_data = {"avatar": ("avatar.jpg", b"dummy_bytes", "image/jpeg")}

    await auth_client.post("profiles/", data=form_data, files=file_data)

    response = await auth_client.post("profiles/", data=form_data, files=file_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "User already has a profile."


@pytest.mark.asyncio
async def test_get_profile_not_found(auth_client):
    """
    Test retrieving a non-existent profile returns 404.
    """
    response = await auth_client.get("profiles/999999/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_all_profiles_success(auth_client):
    """
    Test the endpoint that returns a list of all profiles.
    :param auth_client:
    :return:
    """
    form_data = {
        "first_name": "Alice",
        "last_name": "Wonder",
        "gender": "woman",
        "date_of_birth": "2000-01-01",
        "info": "List info",
    }
    file_data = {"avatar": ("avatar.jpg", b"dummy_bytes", "image/jpeg")}
    await auth_client.post("profiles/", data=form_data, files=file_data)

    response = await auth_client.get("profiles/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "avatar" in data[0]


@pytest.mark.asyncio
async def test_create_profile_unauthorized(client):
    """
    Test that an unauthenticated client cannot access profile creation.
    :param client:
    :return:
    """
    response = await client.post("profiles/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
