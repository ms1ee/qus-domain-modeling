"""Process-wide key/value store shared by the simulator modules.

The store is a simple dictionary that is reset by ``_init()``. Other modules
use it to share the system funds, the rider roster, the order registry and
the simulated clock without passing references through every call.
"""

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global variable store to an empty state."""
    global _global_dict
    _global_dict = {}


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable (e.g. ``"riders"``).
        value: Any Python object to store.
    """
    _global_dict[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key is absent.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _global_dict.get(key, default)
