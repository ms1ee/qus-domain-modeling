"""Global variable store shared across the dispatch simulator.

The store is a simple module-level dictionary. It holds the system funds,
the rider list, the rider ID counter, the running flag, the order list and
the simulated clock. ``_init()`` resets every value to its default.
"""

from typing import Any, Dict

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its default values.

    Default keys:
        funds: System funds (integer, may become negative).
        riders: Dynamic list of Rider objects.
        rider_id_counter: Auto-incrementing counter for rider IDs.
        running: Boolean flag controlling the main loop.
        orders: List of every Order created in this session.
        tick: Current simulated time (one unit per tick).
    """
    _store.clear()
    _store.update(
        {
            "funds": 1000,
            "riders": [],
            "rider_id_counter": 0,
            "running": True,
            "orders": [],
            "tick": 0,
        }
    )


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
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` when the key is missing.
    """
    return _store.get(key, default)


_init()
