"""System-level state management: funds, riders, time and persistence.

This module is the single place where the global simulation state is
initialised and mutated. It also implements automatic rider recruitment.
"""

import json
import logging

import config
import globalvar
from path_planner import LATTICE_NODES, manhattan
from rider import Rider

logger = logging.getLogger(__name__)


def init_system():
    """Initialise all global variables to their startup values.

    Sets funds to the configured initial amount, an empty rider list, the
    rider id counter to 0, the running flag to True, the tick to 0, and an
    empty order list.
    """
    globalvar._init()
    globalvar.set_value("funds", int(config.CONFIG["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    logger.info("System initialised with funds=%s", get_funds())


def get_riders():
    """Return the live list of riders.

    Returns:
        list[Rider]: The global rider list.
    """
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    return riders


def get_funds():
    """Return the current system fund balance."""
    return globalvar.get_value("funds", 0)


def add_funds(amount):
    """Add (or with a negative amount, deduct) funds.

    Args:
        amount: Integer amount to add. May be negative.

    Returns:
        int: The new fund balance.
    """
    new_value = get_funds() + int(amount)
    globalvar.set_value("funds", new_value)
    return new_value


def get_tick():
    """Return the current simulated time."""
    return globalvar.get_value("tick", 0)


def is_running():
    """Return True while the main loop should keep running."""
    return bool(globalvar.get_value("running", False))


def stop_system():
    """Request the main loop to terminate."""
    globalvar.set_value("running", False)


def _next_rider_id():
    """Issue the next unique rider id.

    Returns:
        int: A rider id never returned before in this run.
    """
    counter = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", counter)
    return counter


def _pick_spawn_node(riders):
    """Choose a street intersection far from existing riders.

    Args:
        riders: Current list of riders.

    Returns:
        tuple: ``(x, y)`` lattice node that maximises the minimum distance to
        existing riders.
    """
    if not riders:
        return (400, 400)
    best_node = LATTICE_NODES[0]
    best_distance = -1
    for node in LATTICE_NODES:
        distance = min(manhattan(node, r.position) for r in riders)
        if distance > best_distance:
            best_node, best_distance = node, distance
    return best_node


def recruit_rider(force=False):
    """Create a new rider if funds and capacity allow.

    Args:
        force: When True, ignore the rider cap and funds requirement. The
            cost is still deducted and may make funds negative.

    Returns:
        Rider or None: The new rider, or None when recruitment is refused.
    """
    riders = get_riders()
    cost = int(config.CONFIG["recruit_cost"])
    if not force:
        if len(riders) >= int(config.CONFIG["max_riders"]):
            logger.info("Recruitment refused: rider cap reached")
            return None
        if get_funds() < cost:
            logger.info("Recruitment refused: insufficient funds")
            return None
    add_funds(-cost)
    rider_id = _next_rider_id()
    rider = Rider(rider_id, start=_pick_spawn_node(riders))
    riders.append(rider)
    logger.info("Recruited rider %s (cost %s)", rider_id, cost)
    return rider


def remove_rider(rider_id):
    """Remove an idle rider with no assigned orders.

    Args:
        rider_id: Identifier of the rider to remove.

    Returns:
        bool: True if the rider was removed.
    """
    riders = get_riders()
    for rider in riders:
        if rider.rider_id == rider_id:
            if rider.orders:
                logger.warning("Rider %s has orders and cannot be removed", rider_id)
                return False
            riders.remove(rider)
            return True
    return False


def advance_tick():
    """Advance simulated time by one tick and move every rider.

    Errors raised by an individual rider are logged and do not stop the other
    riders, which keeps the simulation running (error recovery).

    Returns:
        int: The new current tick.
    """
    globalvar.set_value("tick", get_tick() + 1)
    for rider in list(get_riders()):
        try:
            rider.move()
        except Exception:  # noqa: BLE001 - keep the simulation alive
            logger.exception("Rider %s failed to move; state kept", rider.rider_id)
    return get_tick()


def save_snapshot(path):
    """Write the system parameters, riders and orders to a JSON file.

    Args:
        path: Destination file path.

    Returns:
        str: The path written.

    Raises:
        OSError: If the file cannot be written.
    """
    from order import get_all_orders  # local import avoids a module cycle

    data = {
        "funds": get_funds(),
        "tick": get_tick(),
        "config": dict(config.CONFIG),
        "riders": [r.to_dict() for r in get_riders()],
        "orders": [o.to_dict() for o in get_all_orders()],
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    logger.info("State saved to %s", path)
    return path
