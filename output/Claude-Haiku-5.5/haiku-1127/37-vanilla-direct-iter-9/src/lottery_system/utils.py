"""Small helper functions shared across modules."""


def normalize_text(value: str) -> str:
    """Normalize text for case-insensitive, whitespace-insensitive comparison."""
    return " ".join((value or "").split()).casefold()


def ordinal(number: int) -> str:
    """Return the English ordinal form of a positive integer, e.g. 1st, 2nd, 11th."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"
