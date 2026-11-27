"""Small text helpers shared by the services."""

from __future__ import annotations


def normalize_text(text: str | None) -> str:
    """Normalize text for case-insensitive, whitespace-tolerant comparison."""
    return " ".join(str(text or "").split()).casefold()


def same_text(first: str | None, second: str | None) -> bool:
    """Return True if two names/groups are equal after normalization."""
    return normalize_text(first) == normalize_text(second)


def contains_group(department: str | None, groups: list[str]) -> bool:
    """Return True if the department matches any of the given groups."""
    return any(same_text(department, group) for group in groups)
