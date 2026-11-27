"""Global variable storage shared by the food delivery dispatch modules.

The storage is a module-level dictionary. ``_init()`` resets it to the
default contents and is called by ``system.init_system()`` at startup.

Default keys:
    riders (list[Rider]): dynamic list of all riders currently in service.
    current_tick (int): simulated time, advanced once per tick.
    system (SystemManager): the running system manager instance.
"""

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global storage to its default values.

    The rider list starts empty and the simulated time starts at tick 0.
    """
    global _global_dict
    _global_dict = {"riders": [], "current_tick": 0}


def set_value(key: str, value: Any) -> None:
    """Store a value under the given key.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under the given key.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _global_dict.get(key, default)


_init()
