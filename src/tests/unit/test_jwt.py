import pytest

from exceptions import BaseSecurityError
from security.token_manager import JWTAuthManager


@pytest.fixture
def jwt_manager():
    """
    Fixture providing a configured JWTAuthManager instance for testing.
    :return:
    """
    return JWTAuthManager(
        secret_key_access="super_secret_access_key",
        secret_key_refresh="super_secret_refresh_key",
        algorithm="HS256"
    )

def test_create_and_decode_access_token_success(jwt_manager):
    """
    Test that a valid access token can be successfully created and decoded,
    retaining the original payload data (e.g., user_id).
    :param jwt_manager:
    :return:
    """
    user_data = {"user_id": 33}

    token = jwt_manager.create_access_token(user_data)
    decoded_pyaload = jwt_manager.decode_access_token(token)

    assert decoded_pyaload.get("user_id") == 33

def test_decode_invalid_token_raises_error(jwt_manager):
    """
    Test that a BaseSecurityError is raised when attempting to decode
    an invalid, malformed, or fake JWT token.
    :param jwt_manager:
    :return:
    """
    invalid_token = "LORem5ipsum5token233fake"

    with pytest.raises(BaseSecurityError):
        jwt_manager.decode_access_token(invalid_token)