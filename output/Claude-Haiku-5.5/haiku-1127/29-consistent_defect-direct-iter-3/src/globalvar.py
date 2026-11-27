"""Process-wide variable store shared by the dispatch simulator modules.

The store holds the system funds, the rider list (key ``"riders"``), the
rider ID counter, the running flag, the simulated clock, the order list and
the active configuration.
"""

from typing import Any, Dict

from config import DEFAULTS

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its default values.

    Sets funds to the configured initial amount, an empty rider list, the
    rider ID counter to 0, the running flag to True, the clock to 0 and an
    empty order list.
    """
    _store.clear()
    _store.update({
        "config": dict(DEFAULTS),
        "funds": DEFAULTS["initial_funds"],
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "time": 0,
        "orders": [],
    })


def set_value(key: str, value: Any) -> None:
    """Store a value under the given key.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _store[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Retrieve a global variable.

    Args:
        key: Name of the global variable.
        default: Value returned when the key is absent.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _store.get(key, default)


_init()
