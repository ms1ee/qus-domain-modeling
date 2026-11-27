"""Global variable store shared across the simulator modules.

The store is a simple module-level dictionary. Keys used by the program include
``"funds"``, ``"riders"`` (a ``list[Rider]``), ``"rider_id_counter"``,
``"running"``, ``"tick"``, ``"pending_orders"`` and ``"all_orders"``.
"""

from typing import Any

_global_dict: dict = {}


def _init() -> None:
    """Reset the global variable dictionary to an empty state.

    This must be called before any other access, or the store will hold
    whatever values were set previously.
    """
    global _global_dict
    _global_dict = {}


def set_value(key: str, value: Any) -> None:
    """Store a value under the given key.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Retrieve a global variable.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is absent.
    """
    return _global_dict.get(key, default)
