"""Process-wide key/value store used as the system's global variable table.

The store holds the core simulation state such as the system funds, the rider
list (under the key ``"riders"``), the rider ID counter, the running flag and
the simulated tick counter.
"""

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global variable table to an empty state.

    Called once at system start-up (via ``system.init_system``) so that every
    run begins from a clean slate.
    """
    global _global_dict
    _global_dict = {}


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable, e.g. ``"riders"`` or ``"funds"``.
        value: Any Python object to store.
    """
    _global_dict[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when ``key`` is not present.

    Returns:
        The stored value, or ``default`` if the key does not exist.
    """
    return _global_dict.get(key, default)
