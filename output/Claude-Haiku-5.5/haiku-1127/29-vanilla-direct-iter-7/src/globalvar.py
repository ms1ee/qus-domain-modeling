"""Global variable store shared across the simulator modules.

The store is a simple process-wide dictionary. Values are accessed with
:func:`set_value` and :func:`get_value`. Calling :func:`_init` resets every
key to its default value.
"""

from constants import INITIAL_FUNDS

_store = {}


def _init():
    """Reset the global store to the default system parameters.

    Keys initialised:
        funds (int): system fund balance.
        riders (list[Rider]): active rider list.
        rider_id_counter (int): last issued rider id.
        running (bool): main loop control flag.
        tick (int): current simulated time.
        orders (list[Order]): full order history.
        pending_orders (list[Order]): orders waiting for a rider.
    """
    _store.clear()
    _store.update({
        "funds": INITIAL_FUNDS,
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "tick": 0,
        "orders": [],
        "pending_orders": [],
    })


def set_value(key, value):
    """Store ``value`` under ``key``.

    Args:
        key: Hashable identifier of the global value.
        value: Any object to store.
    """
    _store[key] = value


def get_value(key, default=None):
    """Return the value stored under ``key``.

    Args:
        key: Identifier of the global value.
        default: Value returned when ``key`` is missing.

    Returns:
        The stored value, or ``default``.
    """
    return _store.get(key, default)


_init()
