"""Global variable storage."""

_global_dict = {}


def _init():
    """Reset the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store a value."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Fetch a value."""
    return _global_dict.get(key, default)
