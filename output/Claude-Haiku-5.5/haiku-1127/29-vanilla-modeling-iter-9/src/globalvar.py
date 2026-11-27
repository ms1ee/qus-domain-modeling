"""Process-wide storage for simulator state.

The global variable table is a simple dictionary.  Modules access shared
state through :func:`set_value` and :func:`get_value` so that no module
needs to hold its own copy of the system parameters.
"""

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init():
    """Reset the global table to the default system parameters.

    Keys stored:
        funds (int): system funds, initially 1000.
        riders (list): list of ``Rider`` objects.
        rider_id_counter (int): last issued rider ID.
        running (bool): control flag for the main loop.
        simulated_time (int): current simulation tick.
    """
    _global_dict.clear()
    _global_dict.update(
        {
            "funds": 1000,
            "riders": [],
            "rider_id_counter": 0,
            "running": True,
            "simulated_time": 0,
        }
    )


def set_value(key, value):
    """Store ``value`` under ``key`` in the global table.

    Args:
        key (str): variable name, e.g. ``"riders"``.
        value (Any): value to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key (str): variable name.
        default (Any): value returned when the key is missing.

    Returns:
        Any: the stored value or ``default``.
    """
    return _global_dict.get(key, default)


def current_tick():
    """Return the current simulated time as an integer tick count.

    Returns:
        int: the ``simulated_time`` value, or 0 if it is unavailable.
    """
    value = _global_dict.get("simulated_time", 0)
    return value if isinstance(value, int) else 0


_init()
