"""Global variable registry shared by all modules.

Keys used by the system:
    ``riders``            list[Rider]
    ``orders``            list[Order]
    ``rider_id_counter``  int
    ``running``           bool
    ``funds``             int
    ``tick``              int
"""

_global_dict = {}


def _init():
    """Initialise (or reset) the global dictionary."""
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """Store a global value."""
    _global_dict[key] = value


def get_value(key, default=None):
    """Retrieve a global value, returning ``default`` when missing."""
    return _global_dict.get(key, default)
