"""Monetary amount conversion utilities.

IMPORTANT: All monetary values are stored internally as integers representing
cents (e.g. $12.50 is stored as 1250). The API layer serializes these to
float dollar amounts for external consumers. This module provides the
canonical conversion functions — always use these rather than ad-hoc
division/multiplication to avoid floating-point drift.
"""

from typing import Union


def cents_to_dollars(cents: int) -> float:
    """Convert an integer cents value to a float dollar amount.

    Args:
        cents: Amount in cents (must be a non-negative integer).

    Returns:
        Dollar amount as a float, rounded to 2 decimal places.

    Raises:
        ValueError: If cents is negative.
        TypeError: If cents is not an integer.
    """
    if not isinstance(cents, int):
        raise TypeError(f"Expected int for cents, got {type(cents).__name__}")
    if cents < 0:
        raise ValueError(f"Cents must be non-negative, got {cents}")
    return round(cents / 100, 2)


def dollars_to_cents(dollars: Union[float, int, str]) -> int:
    """Convert a dollar amount to integer cents.

    Handles float imprecision by rounding to the nearest cent.

    Args:
        dollars: Dollar amount as float, int, or numeric string.

    Returns:
        Amount in cents as an integer.

    Raises:
        ValueError: If the dollar amount is negative or not parseable.
    """
    try:
        value = float(dollars)
    except (TypeError, ValueError):
        raise ValueError(f"Cannot parse dollar amount: {dollars!r}")
    if value < 0:
        raise ValueError(f"Dollar amount must be non-negative, got {value}")
    return round(value * 100)


def format_dollars(cents: int) -> str:
    """Format a cents value as a dollar string with currency symbol.

    Args:
        cents: Amount in cents.

    Returns:
        Formatted string like "$12.50".
    """
    return f"${cents_to_dollars(cents):.2f}"
