"""Global variable store and system-wide parameters.

This module holds mutable runtime state (system funds, rider roster, the
simulated clock, the order list, the running flag) that is shared between
modules through ``set_value`` and ``get_value``.  It also exposes the static
map geometry and the tunable business parameters in ``PARAMS``.
"""

from typing import Any, Dict

# Map geometry (fixed by the PRD).
MAP_SIZE: int = 800          # 800 x 800 coordinate units
CELL_SIZE: int = 100         # each grid cell is 100 x 100 units
GRID_SIZE: int = 8           # 8 x 8 grid, 64 cells

# Tunable business parameters.  ``load_config`` may override these values.
PARAMS: Dict[str, int] = {
    "initial_funds": 1000,        # starting system funds
    "recruit_cost": 200,          # cost deducted per recruited rider
    "delivery_fee": 50,           # revenue credited per completed delivery
    "max_riders": 10,             # upper bound on the rider roster
    "max_orders_per_rider": 3,    # queue capacity per rider
    "rider_speed_min": 20,        # units per tick
    "rider_speed_max": 30,        # units per tick
    "load_penalty": 150,          # score penalty per queued order (load balancing)
    "log_cap": 5000,              # maximum retained log entries per rider
}

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its startup defaults.

    Sets the system funds to the initial amount, creates an empty rider list,
    sets the rider ID counter to 0, marks the system as running, resets the
    simulated clock and clears the order list.
    """
    _store.clear()
    _store["system_funds"] = PARAMS["initial_funds"]
    _store["riders"] = []
    _store["rider_id_counter"] = 0
    _store["running"] = True
    _store["tick"] = 0
    _store["orders"] = []


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key`` in the global store.

    Args:
        key: Name of the global variable, e.g. ``"riders"``.
        value: Any Python object to store.
    """
    _store[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when ``key`` is absent.

    Returns:
        The stored value, or ``default`` when the key does not exist.
    """
    return _store.get(key, default)


# Initialise the store on import so that the module is usable immediately.
_init()
