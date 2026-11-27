"""Process-wide key/value store shared by the simulator modules.

The store holds the global simulation variables, such as the system funds,
the rider list (key ``"riders"``), the rider ID counter, the running flag and
the current simulated tick. Modules access it through ``set_value`` and
``get_value`` so that no module needs to import another module's state.
"""

from typing import Any, Dict

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store and load the default values.

    Defaults:
        funds: starting balance used for rider recruitment and operations.
        riders: empty list of Rider objects.
        rider_id_counter: 0, so the first rider receives ID 1.
        is_running: True, controls the main loop.
        current_tick: 0, the simulated clock.
    """
    _store.clear()
    _store.update(
        {
            "funds": 2000,
            "riders": [],
            "rider_id_counter": 0,
            "is_running": True,
            "current_tick": 0,
        }
    )


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _store[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _store.get(key, default)
