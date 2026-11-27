"""Global variable store shared by all modules."""

_state = {}


def _init():
    """Reset the global store."""
    global _state
    _state = {}


def set_value(key, value):
    """Store a value under key."""
    _state[key] = value


def get_value(key, default=None):
    """Fetch a value by key (default if missing)."""
    return _state.get(key, default)
