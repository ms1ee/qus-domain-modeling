"""Process-wide key/value store used to share simulator state.

Keys used by the program:
    "funds"             int   system funds (may be negative)
    "riders"            list  list of Rider objects (key "riders": list[Rider])
    "rider_id_counter"  int   last assigned rider id
    "is_running"        bool  main loop control flag
    "orders"            list  list of Order objects
    "order_id_counter"  int   last assigned order id
    "time"              int   current simulation tick
"""

from typing import Any, Dict


def _default_values() -> Dict[str, Any]:
    """Return a fresh dictionary holding the default global values.

    Returns:
        dict: Default values for every global key. Mutable containers are
        newly created on every call so that resets never share state.
    """
    return {
        "funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "is_running": True,
        "orders": [],
        "order_id_counter": 0,
        "time": 0,
    }


_store: Dict[str, Any] = _default_values()


def _init() -> None:
    """Reset the global store to its default values.

    Called at system startup so that every run begins from a clean state.
    """
    _store.clear()
    _store.update(_default_values())


def set_value(key: str, value: Any) -> None:
    """Store a value under the given key.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _store[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Retrieve a global value.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _store.get(key, default)
