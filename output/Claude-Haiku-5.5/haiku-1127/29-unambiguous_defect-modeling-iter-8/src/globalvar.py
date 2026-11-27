"""Global variable store shared by the dispatch system modules.

Values are kept in a module-level dictionary. The key "riders" holds the
list of Rider objects (list[Rider]).
"""

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Initialise the global store with default values."""
    global _global_dict
    _global_dict = {
        "funds": 0,
        "riders": [],
        "rider_id_counter": 0,
        "is_running": True,
        "current_tick": 0,
        "orders": [],
    }


def set_value(key: str, value: Any) -> None:
    """Store a value under the given key.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Retrieve a value from the global store.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _global_dict.get(key, default)


_init()
