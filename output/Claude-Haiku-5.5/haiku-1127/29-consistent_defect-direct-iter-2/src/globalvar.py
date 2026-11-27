"""Global variable store shared by all simulator modules.

The store is a simple dictionary keyed by string names. The key ``"riders"``
holds the list of :class:`rider.Rider` objects. Other keys used by the system
include ``"funds"``, ``"rider_id_counter"``, ``"running"``, ``"tick"`` and
``"orders"``.
"""

from typing import Any, Dict

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to the default system values.

    Sets system funds to 1000, an empty rider list, the rider ID counter to 0,
    the running flag to True, the simulated tick to 0 and an empty order list.
    """
    _store.clear()
    _store.update({
        "funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "tick": 0,
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
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _store.get(key, default)


_init()
