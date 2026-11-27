"""Process-wide key/value store used to share runtime state between modules.

The store holds shared values such as the rider list (key ``"riders"``) and
the simulated clock (key ``"current_tick"``). Call :func:`_init` to reset the
store to its default contents.
"""

from typing import Any, Dict

_global_vars: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store and install the default keys.

    Returns:
        None
    """
    global _global_vars
    _global_vars = {
        "riders": [],
        "current_tick": 0,
    }


def set_value(key: str, value: Any) -> None:
    """Store a value under the given key.

    Args:
        key: Name of the global variable.
        value: Value to store.

    Returns:
        None
    """
    _global_vars[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Fetch a value from the global store.

    Args:
        key: Name of the global variable.
        default: Value returned when the key is missing.

    Returns:
        The stored value, or ``default`` when the key does not exist.
    """
    return _global_vars.get(key, default)


_init()
