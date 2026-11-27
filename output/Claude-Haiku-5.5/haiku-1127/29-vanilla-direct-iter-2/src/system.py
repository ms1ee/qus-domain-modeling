"""System-level state management: funds, riders, time and persistence."""

import json
import logging
from typing import Any, Dict, List, Optional

import globalvar
from rider import (
    DEFAULT_SPEED,
    DEFAULT_START_X,
    DEFAULT_START_Y,
    STATE_IDLE,
    Rider,
)

logger = logging.getLogger(__name__)

# Configurable system parameters (can be overridden by a JSON config file).
PARAMS: Dict[str, int] = {
    "initial_funds": 1000,
    "recruit_threshold": 300,
    "recruit_cost": 300,
    "rider_speed": DEFAULT_SPEED,
    "start_x": DEFAULT_START_X,
    "start_y": DEFAULT_START_Y,
}


def init_system() -> None:
    """Initialize all core global variables.

    Sets system funds, an empty rider list, the rider id counter, the running
    flag, the simulated clock, the pending order queue and the order registry.
    """
    globalvar._init()
    globalvar.set_value("funds", int(PARAMS["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("pending_orders", [])
    globalvar.set_value("all_orders", [])
    globalvar.set_value("order_id_counter", 0)
    logger.info("System initialized with funds=%s", PARAMS["initial_funds"])


# ----------------------------------------------------------------- accessors
def _riders_list() -> List[Rider]:
    """Return the live rider list, creating it if missing."""
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    return riders


def get_riders() -> List[Rider]:
    """Return the list of all riders."""
    return _riders_list()


def get_funds() -> int:
    """Return the current system fund balance."""
    return int(globalvar.get_value("funds", 0) or 0)


def adjust_funds(delta: int) -> int:
    """Add ``delta`` (may be negative) to the system funds.

    Args:
        delta: Amount to add. Negative values deduct funds.

    Returns:
        The new fund balance.
    """
    new_value = get_funds() + int(delta)
    globalvar.set_value("funds", new_value)
    return new_value


def get_tick() -> int:
    """Return the current simulated time in ticks."""
    return int(globalvar.get_value("tick", 0) or 0)


def get_idle_riders() -> List[Rider]:
    """Return all riders currently in the idle state."""
    return [r for r in _riders_list() if r.state == STATE_IDLE]


def find_rider(rider_id: int) -> Optional[Rider]:
    """Look up a rider by id.

    Args:
        rider_id: Identifier to search for.

    Returns:
        The matching rider or None.
    """
    for rider in _riders_list():
        if rider.rider_id == rider_id:
            return rider
    return None


# ------------------------------------------------------------- rider CRUD
def create_rider() -> Rider:
    """Create a new rider with an auto-incremented id at the start position.

    Returns:
        The newly created rider, already appended to the rider list.
    """
    counter = int(globalvar.get_value("rider_id_counter", 0) or 0) + 1
    globalvar.set_value("rider_id_counter", counter)
    rider = Rider(
        counter,
        x=PARAMS["start_x"],
        y=PARAMS["start_y"],
        speed=PARAMS["rider_speed"],
    )
    _riders_list().append(rider)
    logger.info("Created rider #%d", counter)
    return rider


def recruit_if_needed(pending_count: int) -> Optional[Rider]:
    """Recruit a rider when funds allow and pending orders exceed idle riders.

    Args:
        pending_count: Number of orders waiting for assignment.

    Returns:
        The new rider if one was recruited, otherwise None.
    """
    idle = len(get_idle_riders())
    if get_funds() >= PARAMS["recruit_threshold"] and pending_count > idle:
        adjust_funds(-PARAMS["recruit_cost"])
        logger.info("Recruiting rider: pending=%d idle=%d", pending_count, idle)
        return create_rider()
    return None


def remove_rider(rider_id: int) -> bool:
    """Remove an idle rider from the system.

    Args:
        rider_id: Identifier of the rider to remove.

    Returns:
        True if the rider was removed, False if it does not exist.

    Raises:
        ValueError: If the rider still has assigned orders.
    """
    rider = find_rider(rider_id)
    if rider is None:
        return False
    if not rider.is_idle() or rider.orders:
        raise ValueError(f"Rider #{rider_id} is busy and cannot be removed")
    _riders_list().remove(rider)
    logger.info("Removed rider #%d", rider_id)
    return True


# ------------------------------------------------------------- time control
def advance_tick() -> int:
    """Advance the simulation by one tick and move every rider.

    Returns:
        The new tick value.
    """
    tick = get_tick() + 1
    globalvar.set_value("tick", tick)
    for rider in list(_riders_list()):
        rider.move()
    return tick


# ----------------------------------------------------------- consistency
def check_consistency() -> List[str]:
    """Verify and repair the state of riders and their orders.

    Repairs performed:
        * Riders without orders are set to idle.
        * Riders with orders are never idle.
        * Completed orders are removed from rider lists.

    Returns:
        A list of human-readable descriptions of issues that were fixed.
    """
    issues: List[str] = []
    for rider in _riders_list():
        for order in list(rider.orders):
            if getattr(order, "status", "") == "completed":
                rider.orders.remove(order)
                issues.append(f"Removed completed order #{order.id} from rider #{rider.rider_id}")
        if not rider.orders and rider.state != STATE_IDLE:
            rider.state = STATE_IDLE
            issues.append(f"Reset rider #{rider.rider_id} to idle")
        elif rider.orders and rider.state == STATE_IDLE:
            rider.state = 1
            rider.orders[0].status = "picking_up"
            issues.append(f"Rider #{rider.rider_id} had orders while idle; set to picking up")
    for issue in issues:
        logger.warning("Consistency repair: %s", issue)
    return issues


# ------------------------------------------------------------ persistence
def load_config(path: str) -> Dict[str, Any]:
    """Load system parameters from a JSON configuration file.

    The file may contain a ``"params"`` object whose known keys override the
    defaults in :data:`PARAMS`.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        The parsed JSON document.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON is invalid or a parameter is not an integer.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    params = data.get("params", {}) if isinstance(data, dict) else {}
    for key in PARAMS:
        if key in params:
            value = params[key]
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"Parameter '{key}' must be an integer")
            PARAMS[key] = value
    logger.info("Loaded configuration from %s", path)
    return data


def save_config(path: str) -> None:
    """Persist parameters, funds, riders and order history to a JSON file.

    Args:
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    orders = globalvar.get_value("all_orders", []) or []
    pending = globalvar.get_value("pending_orders", []) or []
    data = {
        "params": dict(PARAMS),
        "state": {
            "funds": get_funds(),
            "tick": get_tick(),
            "rider_id_counter": int(globalvar.get_value("rider_id_counter", 0) or 0),
            "order_id_counter": int(globalvar.get_value("order_id_counter", 0) or 0),
        },
        "riders": [r.to_dict() for r in _riders_list()],
        "pending_order_ids": [o.id for o in pending],
        "orders": [o.to_dict() for o in orders],
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    logger.info("Saved state to %s", path)
