"""Process-wide global variable store used by the dispatch simulator.

The store is a simple dictionary wrapped by ``set_value`` and ``get_value``.
Well-known keys used by the program:

* ``"riders"``: ``list[Rider]`` of all currently active riders.
* ``"current_tick"``: ``int`` simulation tick counter.
"""

import logging

logger = logging.getLogger(__name__)

_global_dict = {}


def _init():
    """Reset the global variable store to its default values.

    Creates an empty rider list and sets the simulation tick to zero.
    This function is safe to call multiple times; each call resets state.
    """
    global _global_dict
    _global_dict = {
        "riders": [],
        "current_tick": 0,
    }
    logger.debug("Global variable store initialised.")


def set_value(key, value):
    """Store ``value`` under ``key`` in the global store.

    Args:
        key: Hashable identifier, e.g. ``"riders"``.
        value: Any object to store.
    """
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Identifier used with :func:`set_value`.
        default: Value returned when ``key`` does not exist.

    Returns:
        The stored value, or ``default`` when the key is missing.
    """
    return _global_dict.get(key, default)


_init()
