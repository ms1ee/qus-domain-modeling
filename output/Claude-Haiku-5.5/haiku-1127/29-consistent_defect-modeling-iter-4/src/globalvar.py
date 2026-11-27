"""Process-wide key/value store for the food delivery dispatch simulator.

The store holds shared runtime state such as system funds, the rider list,
the simulated clock, the running flag and the loaded configuration.
Call ``_init()`` to reset the store to its default values.
"""

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its default values.

    Keys initialised here:
        funds (int): system funds, may become negative.
        riders (list[Rider]): dynamic list of riders.
        rider_id_counter (int): last issued rider ID.
        is_running (bool): main loop control flag.
        simulated_time (int): current tick.
        order_manager (OrderManager | None): order manager instance.
        config (dict | None): system parameters.
    """
    global _global_dict
    _global_dict = {
        "funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "is_running": True,
        "simulated_time": 0,
        "order_manager": None,
        "config": None,
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
        The stored value, or ``default``.
    """
    return _global_dict.get(key, default)


_init()
