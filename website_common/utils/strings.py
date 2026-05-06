# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)


def safe_int(value: str, default: int = 0) -> int:
    """
    Safely convert a string value to an integer.

    Attempts to convert the provided string value to an integer. If the conversion
    fails due to invalid format or type, returns the default integer value instead
    of raising an exception.

    Args:
        value (str): The string value to convert to an integer.
        default (int, optional): The default integer value to return if conversion fails.
            Defaults to 0.

    Returns:
        int: The converted integer value, or the default value if conversion fails.

    Examples:
        >>> safe_int("42")
        42
        >>> safe_int("invalid")
        0
        >>> safe_int("invalid", default=10)
        10
        >>> safe_int(None, default=5)
        5
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
