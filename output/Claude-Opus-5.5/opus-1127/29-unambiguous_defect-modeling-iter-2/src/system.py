"""System initialisation, rider recruitment and simulation ticks."""

import logging

import globalvar
from config import DEFAULT_CONFIG
from rider import Rider, RiderState
from path_planner import DEFAULT_GRID

logger = logging.getLogger(__name__)


def init_system(config=None):
    """Initialise all global system parameters.

    :param config: optional dict overriding :data:`DEFAULT_CONFIG`.
    """
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    globalvar._init()
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", int(cfg["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)
    globalvar.set_value("recruitment_cost", int(cfg["recruitment_cost"]))
    globalvar.set_value("max_riders", int(cfg["max_riders"]))
    globalvar.set_value("rider_speed", int(cfg["rider_speed"]))
    logger.info("System initialised with funds %s", cfg["initial_funds"])


def _riders():
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    return riders


def can_recruit():
    """True when funds allow and the rider limit is not reached."""
    funds = globalvar.get_value("funds", DEFAULT_CONFIG["initial_funds"])
    cost = globalvar.get_value("recruitment_cost",
                               DEFAULT_CONFIG["recruitment_cost"])
    max_riders = globalvar.get_value("max_riders", DEFAULT_CONFIG["max_riders"])
    return funds >= cost and len(_riders()) < max_riders


def recruit_rider(force=False):
    """Create a new rider, deducting the recruitment cost.

    :param force: recruit even if funds are insufficient (funds may go
        negative).
    :return: the new Rider, or None if recruitment is not allowed.
    """
    if not force and not can_recruit():
        return None
    funds = globalvar.get_value("funds", DEFAULT_CONFIG["initial_funds"])
    cost = globalvar.get_value("recruitment_cost",
                               DEFAULT_CONFIG["recruitment_cost"])
    counter = (globalvar.get_value("rider_id_counter", 0) or 0) + 1
    globalvar.set_value("rider_id_counter", counter)
    rider = Rider(counter)
    _riders().append(rider)
    globalvar.set_value("funds", int(funds) - int(cost))
    logger.info("Recruited rider %d", counter)
    return rider


def try_recruit_rider():
    """Recruit a rider if allowed, otherwise return None."""
    return recruit_rider(force=False)


def advance_tick():
    """Advance the simulation by one tick and move every rider.

    :return: the new tick number.
    """
    tick = (globalvar.get_value("tick", 0) or 0) + 1
    globalvar.set_value("tick", tick)
    for rider in list(_riders()):
        try:
            rider.move()
        except Exception:  # pragma: no cover - defensive recovery
            logger.exception("Rider %s failed to move; resetting",
                             getattr(rider, "rider_id", "?"))
            try:
                rider.reset()
            except Exception:
                pass
    return tick


def check_consistency():
    """Check and repair global state. Returns a list of applied fixes."""
    fixes = []
    riders = globalvar.get_value("riders")
    if not isinstance(riders, list):
        globalvar.set_value("riders", [])
        fixes.append("rider list reset")
        riders = []
    funds = globalvar.get_value("funds", 0)
    if not isinstance(funds, int) or isinstance(funds, bool):
        try:
            globalvar.set_value("funds", int(funds))
        except (TypeError, ValueError):
            globalvar.set_value("funds", 0)
        fixes.append("funds normalised")
    if not isinstance(globalvar.get_value("orders"), list):
        globalvar.set_value("orders", [])
        fixes.append("order list reset")
    for r in riders:
        if int(r.state) not in (0, 1, 2):
            r.reset()
            fixes.append("rider %d invalid state" % r.rider_id)
        if r.state != RiderState.IDLE and r.current_order is None:
            r.reset()
            fixes.append("rider %d without current order" % r.rider_id)
        cx, cy = DEFAULT_GRID.clamp(r.x), DEFAULT_GRID.clamp(r.y)
        if (cx, cy) != (r.x, r.y):
            r.x, r.y = cx, cy
            fixes.append("rider %d position clamped" % r.rider_id)
    for f in fixes:
        logger.warning("Consistency fix: %s", f)
    return fixes
