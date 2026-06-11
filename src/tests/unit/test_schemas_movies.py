from decimal import Decimal

import pytest
from pydantic import ValidationError

from schemas import MovieCreateSchema


@pytest.fixture
def valid_movie_data():
    """
    Fixture providing a dictionary of valid movie data for schema testing.
    :return:
    """
    return {
        "name": "The Matrix",
        "year": 1999,
        "time": 136,
        "imdb": 8.7,
        "votes": 1700000,
        "price": 14.99,
        "description": (
            "A computer hacker learns from mysterious"
            " rebels about the true nature of his reality."
        ),
        "certification_id": 1,
        "genres": [1, 2],
        "stars": [1, 2],
        "directors": [1],
    }


def test_movie_create_schema_success(valid_movie_data):
    """
    Test that MovieCreateSchema is successfully instantiated with valid data
    and correctly parses data types (e.g., converting price to Decimal).
    :param valid_movie_data:
    :return:
    """
    schema = MovieCreateSchema(**valid_movie_data)

    assert schema.name == "The Matrix"
    assert schema.year == 1999
    assert schema.imdb == 8.7
    assert schema.price == Decimal("14.99")


def test_movie_create_schema_invalid_year(valid_movie_data):
    """
    Test that a ValidationError is raised when the release year is
    historically out of bounds (e.g., prior to the invention of cinema).
    :param valid_movie_data:
    :return:
    """

    invalid_data = valid_movie_data.copy()

    invalid_data["year"] = 1800

    with pytest.raises(ValidationError) as exc_info:
        MovieCreateSchema(**invalid_data)

    assert "year" in str(exc_info.value).lower()


@pytest.mark.parametrize("bad_imdb_score", [-1.5, 11.0, 100.0])
def test_movie_create_schema_invalid_imdb(valid_movie_data, bad_imdb_score):
    """
    Test that a ValidationError is raised when the IMDB score falls
    outside the valid range (e.g., negative values or greater than 10.0).
    :param valid_movie_data:
    :param bad_imdb_score:
    :return:
    """
    invalid_data = valid_movie_data.copy()
    invalid_data["imdb"] = bad_imdb_score

    with pytest.raises(ValidationError) as exc_info:
        MovieCreateSchema(**invalid_data)

    assert "imdb" in str(exc_info.value).lower()


def test_movie_create_schema_invalid_price(valid_movie_data):
    """
    Test that a ValidationError is raised when a negative price is provided.
    :param valid_movie_data:
    :return:
    """
    invalid_data = valid_movie_data.copy()
    invalid_data["price"] = -5.00

    with pytest.raises(ValidationError) as exc_info:
        MovieCreateSchema(**invalid_data)

    assert "price" in str(exc_info.value).lower()
