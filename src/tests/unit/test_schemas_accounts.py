import pytest
from pydantic import ValidationError

from schemas import UserRegistrationRequestSchema


def test_user_registration_schema_success():
    """
    Test that a user can successfully register with a valid
     email and a strong password.
    :return:
    """
    valid_data = {"email": "test@example.com", "password": "Strong_e!le123"}

    schema = UserRegistrationRequestSchema(**valid_data)

    assert schema.email == "test@example.com"
    assert schema.password == "Strong_e!le123"


def test_user_registration_schema_invalid_email():
    """
    Test that registration fails and raises a ValidationError when
     an invalid email format is provided.
    :return:
    """
    invalid_data = {"email": "not-an-email-at-all", "password": "some_password"}

    with pytest.raises(ValidationError):
        UserRegistrationRequestSchema(**invalid_data)


def test_user_registration_schema_missing_fields():
    """
    Test that a ValidationError is raised when required
     fields (e.g., password) are missing.
    :return:
    """
    missing_data = {"email": "test@example.com"}

    with pytest.raises(ValidationError) as exc_info:
        UserRegistrationRequestSchema(**missing_data)

    assert "password" in str(exc_info.value)
