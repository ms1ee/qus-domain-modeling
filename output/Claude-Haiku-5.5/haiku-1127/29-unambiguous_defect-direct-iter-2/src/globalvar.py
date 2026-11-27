"""Process-wide key/value store shared by the dispatch simulator modules.

The store holds the mutable global state of the simulation, such as the
rider list (key ``"riders"``), system funds, the rider ID counter, the
running flag and the simulated tick counter.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

_globals: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its default values.

    Creates an empty rider list, a zeroed rider ID counter, the running flag
    set to True and an empty order history. Funds and parameters are filled
    in later by :func:`system.init_system`.
    """
    _globals.clear()
    _globals.update(
        {
            "riders": [],
            "funds": 0,
            "rider_id_counter": 0,
            "running": True,
            "tick": 0,
            "orders": [],
            "params": {},
        }
    )
    logger.debug("Global variable store initialised")


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable, e.g. ``"riders"``.
        value: Any Python object to store.
    """
    _globals[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when ``key`` has not been set.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _globals.get(key, default)


# Make sure the store is always usable, even before init_system() runs.
_init()
