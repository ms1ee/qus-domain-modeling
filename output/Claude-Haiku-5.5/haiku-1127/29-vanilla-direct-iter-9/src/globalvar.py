"""Global variable storage for the food delivery dispatch simulator.

Shared runtime state (system funds, rider list, rider ID counter, running
flag, simulated time, order history and configuration) is kept in a single
module-level dictionary so that every module reads and updates it through the
same place.
"""

from typing import Any, Dict

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Initialise, or reset, all global variables to their default values.

    Keys stored:
        system_funds (int): available funds, may become negative.
        riders (list[Rider]): riders currently in service.
        rider_id_counter (int): last issued rider ID.
        running (bool): control flag for the main loop.
        time (int): current simulation tick.
        orders (list[Order]): every order created so far.
        config (dict): system parameters.
    """
    global _global_dict
    _global_dict = {
        "system_funds": 1000,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "time": 0,
        "orders": [],
        "config": {},
    }


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
        The stored value, or ``default`` if the key is absent.
    """
    return _global_dict.get(key, default)


_init()
