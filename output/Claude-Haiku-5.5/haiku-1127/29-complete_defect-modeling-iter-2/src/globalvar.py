"""Process-wide global variable store used by the dispatch simulator."""

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its default values.

    Default keys:
        riders: empty list of Rider objects.
        rider_id_counter: 0, used to generate unique rider IDs.
        running_state: True, controls the main loop.
        simulated_time: 0 ticks.
        funds: 0 system funds.
    """
    global _global_dict
    _global_dict = {
        "riders": [],
        "rider_id_counter": 0,
        "running_state": True,
        "simulated_time": 0,
        "funds": 0,
    }


def set_value(key: str, value: Any) -> None:
    """Store a value under the given key.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_dict[key] = value


def get_value(key: str) -> Any:
    """Return the value stored under the given key.

    Args:
        key: Name of the global variable.

    Returns:
        The stored value, or None if the key does not exist.
    """
    return _global_dict.get(key)


_init()
