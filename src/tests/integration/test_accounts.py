import pytest
from fastapi import status
from sqlalchemy import select

from database import UserModel, ActivationTokenModel, UserGroupModel, UserGroupEnum
from security.passwords import hash_password


@pytest.mark.asyncio
async def test_register_user_success(client, db_session):
    """
    Test successful user registration.
    Verifies that:
    1. The API returns a 201 Created status.
    2. The user is saved to the database.
    3. The new user's status is inactive by default.
    4. An activation token is successfully generated and linked to the user.
    :param client:
    :param db_session:
    :return:
    """
    register_payload = {"email": "test@gmail.com", "password": "Strong_password1234@!"}

    response = await client.post("accounts/register/", json=register_payload)

    assert response.status_code == status.HTTP_201_CREATED

    response_data = response.json()
    assert response_data["email"] == "test@gmail.com"
    assert "id" in response_data

    stmt = select(UserModel).where(UserModel.email == "test@gmail.com")
    result = await db_session.execute(stmt)
    db_user = result.scalar_one_or_none()

    assert db_user is not None
    assert db_user.is_active is False

    token_stmt = select(ActivationTokenModel).where(
        ActivationTokenModel.user_id == db_user.id
    )
    token_result = await db_session.execute(token_stmt)
    db_token = token_result.scalar_one_or_none()

    assert db_token is not None


@pytest.mark.asyncio
async def test_register_user_duplicate_email_fails(client, db_session):
    """
    Test that registering a user with an already existing email fails.
    Verifies that the API correctly rejects the duplicate entry and
    returns a 409 Conflict status code.
    :param client:
    :param db_session:
    :return:
    """
    group_stmt = select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    group_result = await db_session.execute(group_stmt)
    user_group = group_result.scalar_one()

    existing_user = UserModel(
        email="test1@gmail.com",
        _hashed_password=hash_password("Password1234@!"),
        group_id=user_group.id,
        is_active=False,
    )
    db_session.add(existing_user)
    await db_session.commit()

    register_payload = {"email": "test1@gmail.com", "password": "Password1234@!"}

    response = await client.post("accounts/register/", json=register_payload)
    assert response.status_code == status.HTTP_409_CONFLICT

    response_data = response.json()
    assert "detail" in response_data


@pytest.mark.asyncio
async def test_user_login_success(client, db_session):
    """
    Test successful user login.
    Verifies that an active user providing correct credentials receives
    a 200 OK status along with valid access and refresh JWT tokens.
    :param client:
    :param db_session:
    :return:
    """
    group_stmt = select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    group_result = await db_session.execute(group_stmt)
    user_group = group_result.scalar_one()

    raw_password = "Super_secure_password123!"
    active_user = UserModel(
        email="login_me@example.com",
        _hashed_password=hash_password(raw_password),
        is_active=True,
        group_id=user_group.id,
    )

    db_session.add(active_user)
    await db_session.commit()

    login_payload = {"email": "login_me@example.com", "password": raw_password}

    response = await client.post("accounts/login/", json=login_payload)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "access_token" in response_data
    assert "refresh_token" in response_data


@pytest.mark.asyncio
async def test_user_login_wrong_password_fails(client, db_session):
    """
    Test user login failure due to incorrect credentials.
    Verifies that attempting to log in with a wrong password
    returns a 401 Unauthorized status code.
    :param client:
    :param db_session:
    :return:
    """
    group_stmt = select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    group_result = await db_session.execute(group_stmt)
    user_group = group_result.scalar_one()

    active_user = UserModel(
        email="wrong_pass@example.com",
        _hashed_password=hash_password("CorrectPassword123!"),
        is_active=True,
        group_id=user_group.id,
    )
    db_session.add(active_user)
    await db_session.commit()

    login_payload = {
        "email": "wrong_pass@example.com",
        "password": "InCorrectPasswor112d!",
    }
    response = await client.post("accounts/login/", json=login_payload)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_activate_account_success(client, db_session):
    """
    Test successful account activation.
    Verifies that providing a valid activation token and email returns
    a 200 OK status and successfully updates the user's 'is_active'
    flag to True in the database.
    :param client:
    :param db_session:
    :return:
    """
    group_stmt = select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    result = await db_session.execute(group_stmt)
    db_group = result.scalar_one_or_none()

    user = UserModel(
        email="test_activate_user@gmail.com",
        _hashed_password=hash_password("CorrectPassword123!"),
        group_id=db_group.id,
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()

    token = ActivationTokenModel(user_id=user.id)
    db_session.add(token)
    await db_session.commit()

    response = await client.post(
        "accounts/activate/",
        json={"token": str(token.token), "email": "test_activate_user@gmail.com"},
    )

    assert response.status_code == status.HTTP_200_OK

    await db_session.refresh(user)
    assert user.is_active is True
