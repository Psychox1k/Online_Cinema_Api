from datetime import date, timedelta
from io import BytesIO

import pytest
from PIL import Image
from fastapi import UploadFile

from validation import (
    validate_name,
    validate_gender,
    validate_birth_date,
    validate_image
)


def test_validate_name_success():
    """
    Test that valid names consisting only of English
    letters pass validation without errors.
    :return:
    """
    validate_name("John")
    validate_name("Katerina")


def test_validate_name_invalid_characters():
    """
    Test that a ValueError is raised when a name contains invalid characters,
    numbers, or non-English letters.
    :return:
    """
    with pytest.raises(ValueError) as exc:
        validate_name("John123")
    assert "contains non-english letters" in str(exc.value).lower()


def test_validate_gender_success():
    """
    Test that valid gender strings are accepted without errors.
    :return:
    """
    validate_gender("man")


def test_validate_invalid_gender_error():
    """
    Test that a ValueError is raised when an unsupported
    or invalid gender is provided.
    :return:
    """
    with pytest.raises(ValueError) as exc:
        validate_gender("BABY ALIEN")
    assert "gender must be one of:" in str(exc.value).lower()


def test_validate_birth_date_success():
    """
    Test that a valid birth date (e.g., an adult under the maximum age limit)
    passes validation.
    :return:
    """
    valid_date = date.today() - timedelta(days=365 * 20)
    validate_birth_date(valid_date)


def test_validate_birth_date_too_old():
    """
    Test that a ValueError is raised if the birth date is historically
     out of bounds (e.g., older than the year 1900).
    :return:
    """
    with pytest.raises(ValueError) as exc:
        validate_birth_date(date(1899, 12, 31))
    assert "year must be greater than 1900" in str(exc.value).lower()


def test_validate_birth_date_underage():
    """
    Test that a ValueError is raised if the user is under the minimum
    required age (e.g., under 18).
    :return:
    """
    with pytest.raises(ValueError) as exc:
        validate_birth_date(date(2020, 12, 12))
    assert "at least 18 years old" in str(exc.value).lower()


def create_dummy_upload_file(
        image_format: str, size_bytes: int = 180
) -> UploadFile:
    """
    Helper function to generate a dummy UploadFile in
    memory for testing purposes.
    :param image_format:
    :param size_bytes:
    :return:
    """
    file_obj = BytesIO()

    if image_format == "TXT":
        file_obj.write(b"Hello_world" * size_bytes)
    else:
        image = Image.new("RGB", (10, 10), color="red")
        image.save(file_obj, format=image_format)

    if size_bytes > 100 and image_format != "TXT":
        # Pad the file to reach the desired size
        file_obj.write(b"0" * size_bytes)

    file_obj.seek(0)

    # Fixed the missing parentheses on lower()
    return UploadFile(file=file_obj, filename=f"test.{image_format.lower()}")


def test_validate_image_success():
    """
    Test that a properly formatted image within the accepted
    size limits passes validation.
    :return:
    """
    valid_file = create_dummy_upload_file(image_format="jpeg")
    validate_image(valid_file)


def test_validate_image_too_large():
    """
    Test that a ValueError is raised when the uploaded image
    exceeds the maximum allowed file size.
    :return:
    """
    large_file = create_dummy_upload_file(
        image_format="jpeg", size_bytes=(1024 * 1024 + 10)
    )

    with pytest.raises(ValueError) as exc:
        validate_image(large_file)

    assert "size" in str(exc.value).lower()


def test_validate_image_invalid_format():
    """
    Test that a ValueError is raised when the
    uploaded file is not a valid image format.
    :return:
    """
    text_file = create_dummy_upload_file(image_format="TXT")

    with pytest.raises(ValueError) as exc:
        validate_image(text_file)
    assert "invalid image format" in str(exc.value).lower()