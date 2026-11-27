"""Global variable store shared by all simulator modules.

The store is a plain dictionary wrapped by ``set_value`` / ``get_value`` so
that every module reads and writes the same system state (funds, rider list,
rider ID counter, running flag, simulated clock, configuration parameters).
"""

from typing import Any, Dict

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to the default system parameters.

    Defaults:
        funds: 0 (may become negative).
        riders: empty list of Rider objects.
        rider_id_counter: 0.
        running_state: True.
        simulated_time: 0 ticks.
        orders: empty list of Order objects.
        next_order_id: 1.
        order_fee: 100 funds charged per accepted order.
        recruit_threshold: 300 funds needed to trigger recruitment.
        recruit_cost: 300 funds deducted for each recruited rider.
        rider_speed: 50 units per tick.
        max_ticks: 10000 safety cap for ticks spent on one order.
    """
    _store.clear()
    _store.update(
        {
            "funds": 0,
            "riders": [],
            "rider_id_counter": 0,
            "running_state": True,
            "simulated_time": 0,
            "orders": [],
            "next_order_id": 1,
            "order_fee": 100,
            "recruit_threshold": 300,
            "recruit_cost": 300,
            "rider_speed": 50,
            "max_ticks": 10000,
        }
    )


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable.
        value: Any Python object to store.
    """
    _store[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key`` or ``default`` when missing.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default``.
    """
    return _store.get(key, default)


_init()
