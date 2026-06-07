import pytest
from fastapi import status
from sqlalchemy import select

from database import ActivationTokenModel, UserModel


@pytest.mark.asyncio
async def test_e2e_auth_flow_register_and_login(client, db_session):
    """
    E2E Scenario: A new user registers, retrieves an access token,
    and successfully accesses a protected endpoint.
    :param client:
    :return:
    """

    user_email = "new_e2e_user@cinema.com"
    user_password = "StrongPassword123x!"

    # STEP 1: Register
    register_payload = {"email": user_email, "password": user_password}
    await client.post("accounts/register/", json=register_payload)

    # STEP 2: Fetch activation code from the database
    stmt = select(ActivationTokenModel).join(UserModel).where(
        UserModel.email == user_email
    )

    result = await db_session.execute(stmt)
    activation_obj = result.scalar_one_or_none()
    activation_token = activation_obj.token

    # STEP 3: Activate account
    activation_payload = {"email": user_email, "token": activation_token}
    act_response = await client.post(
        "accounts/activate/",
        json=activation_payload
    )

    assert act_response.status_code == status.HTTP_200_OK

    # STEP 4: Login
    login_data = {"email": user_email, "password": user_password}
    login_response = await client.post("accounts/login/", json=login_data)
    assert login_response.status_code == status.HTTP_200_OK

    token_data = login_response.json()
    assert "access_token" in token_data
    access_token = token_data["access_token"]

    profile_data = {
        "first_name": "David",
        "last_name": "Klymnko",
        "gender": "man",
        "date_of_birth": "2000-01-01",
        "info": "Law student"
    }

    files = {"avatar": ("test.jpg", b"fake_image_content", "image/jpeg")}


    await client.post(
        "profiles/",
        data=profile_data,
        files=files,
        headers={"Authorization": f"Bearer {access_token}"}
    )

    headers = {"Authorization": f"Bearer {access_token}"}
    profile_response = await client.get("profiles/me/", headers=headers)

    assert profile_response.status_code == status.HTTP_200_OK

    profile_json = profile_response.json()
    assert profile_json["first_name"] == "David"
    assert profile_json["last_name"] == "Klymnko"
    assert "user_id" in profile_json