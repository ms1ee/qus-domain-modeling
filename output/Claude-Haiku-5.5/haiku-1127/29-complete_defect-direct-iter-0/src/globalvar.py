"""Global variable store shared by all simulator modules.

The store is a simple dictionary wrapped by ``set_value`` and ``get_value``.
Well-known keys:

* ``"riders"``: ``list[Rider]`` - the dynamic rider list (CRUD operations).
* ``"orders"``: ``list[Order]`` - every order created in this session.
* ``"funds"``: ``int`` - system fund balance (may be negative).
* ``"rider_id_counter"``: ``int`` - last issued rider ID.
* ``"order_id_counter"``: ``int`` - last issued order ID.
* ``"tick"``: ``int`` - current simulated time.
* ``"running"``: ``bool`` - main loop control flag.
"""

from typing import Any, Dict

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its default values.

    Riders list is empty, rider ID counter is 0, the system is running and
    the simulated clock starts at tick 0.
    """
    global _store
    _store = {
        "riders": [],
        "rider_id_counter": 0,
        "order_id_counter": 0,
        "orders": [],
        "funds": 0,
        "tick": 0,
        "running": True,
    }


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
        The stored value, or ``default`` if the key is missing.
    """
    return _store.get(key, default)


def next_counter(key: str) -> int:
    """Increment an integer counter stored under ``key`` and return it.

    Args:
        key: Name of the counter variable.

    Returns:
        The new (incremented) counter value, starting at 1.
    """
    value = int(_store.get(key, 0)) + 1
    _store[key] = value
    return value


_init()
