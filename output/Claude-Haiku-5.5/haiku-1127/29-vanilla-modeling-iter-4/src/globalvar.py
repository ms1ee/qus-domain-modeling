"""Process-wide global variable store.

The store holds shared runtime values such as the rider list, the current
simulation tick and the system running flag. Modules read and write values
through :func:`get_value` and :func:`set_value` instead of importing each
other's mutable state directly.
"""

import logging

logger = logging.getLogger(__name__)

_global_dict = {}


def _init():
    """Reset the global variable table to its default values.

    Defaults:
        riders: empty rider list (key ``"riders"`` holds ``list[Rider]``).
        funds: system funds, starting at 1000.
        rider_id_counter: last issued rider ID, starting at 0.
        is_running: main loop control flag, starting at True.
        current_time: simulated tick counter, starting at 0.
    """
    global _global_dict
    _global_dict = {
        "riders": [],
        "funds": 1000,
        "rider_id_counter": 0,
        "is_running": True,
        "current_time": 0,
    }
    logger.debug("Global variable table initialised")


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Any Python object to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when ``key`` is not present.

    Returns:
        The stored value, or ``default`` when the key does not exist.
    """
    return _global_dict.get(key, default)


_init()
