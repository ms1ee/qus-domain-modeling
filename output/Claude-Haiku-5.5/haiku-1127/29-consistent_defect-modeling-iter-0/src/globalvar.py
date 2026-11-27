"""Global variable store used to share system state between modules.

The store is a simple module-level dictionary. The key ``"riders"`` holds the
``list[Rider]`` managed by the system.
"""

from typing import Any, Dict

_global_vars: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global variable store to an empty dictionary.

    This must be called before any other access when a fresh simulation is
    started.
    """
    global _global_vars
    _global_vars = {}


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable, e.g. ``"riders"``.
        value: Value to store.
    """
    _global_vars[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _global_vars.get(key, default)


_init()
