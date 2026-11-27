"""Global variable storage shared across the simulator."""

_global_dict = {}


def _init():
    """Reset all global state to its defaults."""
    global _global_dict
    _global_dict = {
        "funds": 300,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "tick": 0,
        "orders": [],
    }


def set_value(key, value):
    """Set a global value."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Get a global value (default if missing)."""
    return _global_dict.get(key, default)


_init()
