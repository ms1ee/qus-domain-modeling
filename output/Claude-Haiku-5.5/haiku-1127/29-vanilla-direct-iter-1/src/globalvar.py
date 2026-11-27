"""Global variable storage shared by all simulator modules.

The storage is a simple module-level dictionary. Keys used by the program:

* ``funds``            - system funds (int, may be negative)
* ``riders``           - list of Rider objects (key "riders": list[Rider])
* ``rider_id_counter`` - last issued rider id
* ``running``          - main loop control flag (bool)
* ``time``             - simulated tick counter (int)
* ``pending_orders``   - orders waiting for a rider
* ``orders``           - full order history
"""

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global storage to its initial values.

    Lists are re-created so that repeated initialisation never shares state
    with a previous run.
    """
    global _global_dict
    _global_dict = {
        "funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "time": 0,
        "pending_orders": [],
        "orders": [],
    }


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _global_dict.get(key, default)


_init()
