"""Process-wide key/value store shared by all dispatch modules.

Keys used by the program:
    riders            list[Rider]   active riders
    rider_id_counter  int           last rider ID issued
    orders            list[Order]   every order created in this session
    pending_orders    list[Order]   orders waiting for a rider
    order_id_counter  int           last order ID issued
    funds             int           system fund balance (may go negative)
    running           bool          main loop control flag
    tick              int           simulated time (one unit per tick)
    initial_funds, recruit_threshold, recruit_cost, delivery_fee,
    default_speed, max_ticks_per_order   configurable system parameters
"""

import copy

_DEFAULTS = {
    "initial_funds": 300,
    "recruit_threshold": 300,
    "recruit_cost": 300,
    "delivery_fee": 100,
    "default_speed": 50,
    "max_ticks_per_order": 2000,
}

_store = {}


def _init():
    """Reset every global value to its startup default.

    Rider list is empty, rider ID counter is 0, the system is running,
    simulated time is 0 and funds are set to the configured initial funds.
    """
    _store.clear()
    _store.update(
        {
            "riders": [],
            "rider_id_counter": 0,
            "orders": [],
            "pending_orders": [],
            "order_id_counter": 0,
            "funds": _DEFAULTS["initial_funds"],
            "running": True,
            "tick": 0,
        }
    )
    _store.update(copy.deepcopy(_DEFAULTS))


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global value.
        value: Any Python object to store.
    """
    _store[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Name of the global value.
        default: Value returned when the key does not exist.

    Returns:
        The stored value or ``default``.
    """
    return _store.get(key, default)


_init()
