"""Global variable storage shared by the dispatch simulator modules.

The storage is a simple module-level dictionary. ``_init()`` resets it to the
default values and is invoked when the module is imported as well as by
``system.init_system()``.
"""

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global storage to its default values.

    Default keys:
        riders: list of Rider objects (empty list at startup).
        current_tick: simulated time counter, starts at 0.
    """
    global _global_dict
    _global_dict = {
        "riders": [],
        "current_tick": 0,
    }


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key: str) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.

    Returns:
        The stored value, or ``None`` if the key does not exist.
    """
    return _global_dict.get(key)


_init()
