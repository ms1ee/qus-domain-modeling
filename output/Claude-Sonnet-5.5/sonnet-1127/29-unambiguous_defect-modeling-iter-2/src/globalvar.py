"""Simple global variable store shared by all modules."""

_data = {}


def _init():
    """Reset the global store."""
    global _data
    _data = {
        "funds": 0,
        "riders": [],
        "orders": [],
        "rider_id_counter": 0,
        "running": True,
        "tick": 0,
    }


def set_value(key, value):
    """Set a global value."""
    _data[key] = value


def get_value(key, default=None):
    """Get a global value (default if missing)."""
    return _data.get(key, default)


_init()
