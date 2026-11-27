"""Process-wide variable store shared by the dispatch modules.

Keys used by the system:
    funds, riders (list of Rider), rider_id_counter, is_running,
    current_tick, order_id_counter, rider_speed, rider_start,
    recruit_cost, recruit_threshold.
"""

from typing import Any, Dict

import config

_global_dict: Dict[str, Any] = {}


def _init() -> None:
    """Reset the global store to its default values.

    This restores funds, an empty rider list, counters, the running flag and
    the rider start parameters.
    """
    global _global_dict
    _global_dict = {
        "funds": config.INITIAL_FUNDS,
        "riders": [],
        "rider_id_counter": 0,
        "is_running": True,
        "current_tick": 0,
        "order_id_counter": 0,
        "rider_speed": config.RIDER_SPEED,
        "rider_start": (config.RIDER_START_X, config.RIDER_START_Y),
        "recruit_cost": config.RECRUIT_COST,
        "recruit_threshold": config.RECRUIT_THRESHOLD,
    }


def set_value(key: str, value: Any) -> None:
    """Store ``value`` under ``key``.

    Args:
        key: Variable name, e.g. ``"riders"``.
        value: Any Python object to store.
    """
    _global_dict[key] = value


def get_value(key: str, default: Any = None) -> Any:
    """Return the value stored under ``key``.

    Args:
        key: Variable name.
        default: Value returned when the key is absent.

    Returns:
        The stored value or ``default``.
    """
    return _global_dict.get(key, default)


_init()
