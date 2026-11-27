"""Process-wide key/value store shared by the simulator modules.

The store holds shared runtime state such as the live rider list and the
simulation clock, so that modules can reach it without creating circular
imports between each other.
"""

from typing import Any, Dict

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its default values.

    Defaults:
        riders: an empty list that will hold ``Rider`` objects.
        current_tick: simulation clock, starting at 0.
    """
    _store.clear()
    _store["riders"] = []
    _store["current_tick"] = 0


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _store[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key is missing.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _store.get(key, default)


# Make the store usable immediately after import.
_init()
