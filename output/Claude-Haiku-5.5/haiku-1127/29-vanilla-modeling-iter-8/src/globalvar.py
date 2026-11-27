"""Global variable storage shared by all simulator modules.

The store is a plain dictionary keyed by variable name. ``_init`` resets
every variable to its default value and is invoked on import so that
``get_value`` is always usable.
"""

from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, int] = {
    "initial_funds": 1000,
    "recruit_cost": 300,
    "recruit_fund_threshold": 300,
    "max_run_ticks": 2000,
}

_store: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its default values.

    Defaults:
        funds: 1000
        riders: empty list
        rider_id_counter: 0
        is_running: True
        orders / pending_orders: empty lists
        tick: 0
        config: copy of DEFAULT_CONFIG
    """
    _store.clear()
    _store.update(
        {
            "funds": DEFAULT_CONFIG["initial_funds"],
            "riders": [],
            "rider_id_counter": 0,
            "is_running": True,
            "orders": [],
            "pending_orders": [],
            "tick": 0,
            "config": dict(DEFAULT_CONFIG),
        }
    )


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Name of the global variable (e.g. ``"riders"``).
        value: Value to store.
    """
    _store[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the global variable stored under ``key``.

    Args:
        key: Name of the global variable.
        default: Value returned when the key does not exist.

    Returns:
        The stored value, or ``default`` if the key is missing.
    """
    return _store.get(key, default)


_init()
