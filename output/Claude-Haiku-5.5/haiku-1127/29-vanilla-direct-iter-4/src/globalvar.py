"""Process-wide global variable store for the dispatch simulator.

Keys used across the program:
    funds (int): system funds, may become negative.
    riders (list[Rider]): active rider objects.
    rider_id_counter (int): last issued rider id.
    running (bool): main loop control flag.
    tick (int): current simulated time in ticks.
    orders (list[Order]): every order created in this session.
    pending_orders (list[Order]): orders waiting for a rider.
    order_counter (int): last issued order id.
"""

from typing import Any, Dict

_global_vars: Dict[str, Any] = {}


def _init() -> None:
    """Reset all global variables to their startup defaults.

    Sets system funds to 1000, an empty rider list, the rider id counter to 0,
    the running flag to True and the simulated clock to tick 0.
    """
    _global_vars.clear()
    _global_vars.update(
        {
            "funds": 1000,
            "riders": [],
            "rider_id_counter": 0,
            "running": True,
            "tick": 0,
            "orders": [],
            "pending_orders": [],
            "order_counter": 0,
        }
    )


def set_value(key: str, value: Any) -> None:
    """Store a value under the given global key.

    Args:
        key: Name of the global variable.
        value: Value to store.
    """
    _global_vars[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under the given global key.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` when the key is missing.
    """
    return _global_vars.get(key, default)


_init()
