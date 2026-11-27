"""Global state storage shared across modules."""

_global_dict = {}


def _init():
    """Reset the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store a value under key."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Return the value stored under key, or default."""
    return _global_dict.get(key, default)
