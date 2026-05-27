# validation/movies.py
from decimal import Decimal
from typing import Optional


def validate_year(value: Optional[int]) -> Optional[int]:
    if value is not None and value < 1888:
        raise ValueError("Year must be >= 1888")
    return value


def validate_imdb(value: Optional[float]) -> Optional[float]:
    if value is not None and not (0 <= value <= 10):
        raise ValueError("IMDb rating must be between 0 and 10")
    return value


def validate_price(value: Optional[Decimal]) -> Optional[Decimal]:
    if value is not None and value < 0:
        raise ValueError("Price must be >= 0")
    return value