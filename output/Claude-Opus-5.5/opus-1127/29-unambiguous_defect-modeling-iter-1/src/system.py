"""System initialisation, rider recruitment and simulation clock."""

import logging

import config
import globalvar
import order_model
from rider import Rider, RiderState

logger = logging.getLogger(__name__)


def init_system(cfg=None):
    """Initialise all global system parameters.

    Returns a :class:`SystemManager` wrapping the global state.
    """
    values = dict(config.DEFAULT_CONFIG)
    if isinstance(cfg, dict):
        values.update(cfg)
    globalvar._init()
    globalvar.set_value("config", values)
    globalvar.set_value("funds", int(values["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("recruitment_cost", int(values["recruitment_cost"]))
    globalvar.set_value("default_speed", int(values["default_speed"]))
    globalvar.set_value("max_riders", int(values["max_riders"]))
    globalvar.set_value("start_pos", (int(values["start_x"]), int(values["start_y"])))
    order_model.reset_order_ids()
    return SystemManager()


def _ensure_initialised():
    if globalvar.get_value("riders") is None:
        init_system()


def can_recruit():
    """Return True if funds allow recruiting and the rider cap isn't hit."""
    _ensure_initialised()
    funds = globalvar.get_value("funds", 0)
    cost = globalvar.get_value("recruitment_cost", 0)
    max_riders = globalvar.get_value("max_riders", 20)
    return funds >= cost and len(globalvar.get_value("riders")) < max_riders


def recruit_rider(force=False):
    """Recruit a new rider, deducting the recruitment cost.

    Returns the new Rider, or None if recruitment is not allowed
    (unless ``force`` is True, in which case funds may go negative).
    """
    _ensure_initialised()
    if not force and not can_recruit():
        return None
    counter = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", counter)
    rider = Rider(counter)
    globalvar.set_value("funds", globalvar.get_value("funds", 0)
                        - globalvar.get_value("recruitment_cost", 0))
    globalvar.get_value("riders").append(rider)
    logger.info("Recruited rider %d", counter)
    return rider


def check_consistency():
    """Repair inconsistent state; returns a list of issue descriptions."""
    issues = []
    riders = globalvar.get_value("riders")
    if not isinstance(riders, list):
        globalvar.set_value("riders", [])
        issues.append("rider list was invalid and has been reset")
        riders = []
    seen = set()
    for r in list(riders):
        if r.rider_id in seen:
            issues.append("duplicate rider id %d removed" % r.rider_id)
            riders.remove(r)
            continue
        seen.add(r.rider_id)
        if r.state != RiderState.IDLE and not r.orders:
            r.state = RiderState.IDLE
            r.route = []
            issues.append("rider %d had no orders but was busy" % r.rider_id)
        if r.state not in (0, 1, 2):
            r.state = RiderState.IDLE
            issues.append("rider %d had invalid state" % r.rider_id)
    if seen and globalvar.get_value("rider_id_counter", 0) < max(seen):
        globalvar.set_value("rider_id_counter", max(seen))
        issues.append("rider id counter corrected")
    if not isinstance(globalvar.get_value("funds"), int):
        try:
            globalvar.set_value("funds", int(globalvar.get_value("funds")))
        except (TypeError, ValueError):
            globalvar.set_value("funds", 0)
        issues.append("funds value corrected")
    for issue in issues:
        logger.warning("Consistency: %s", issue)
    return issues


def advance_time(ticks=1):
    """Advance the simulation by ``ticks`` ticks, moving every rider."""
    _ensure_initialised()
    for _ in range(max(0, int(ticks))):
        tick = globalvar.get_value("tick", 0) + 1
        globalvar.set_value("tick", tick)
        for r in list(globalvar.get_value("riders", [])):
            try:
                r.move()
            except Exception:  # pragma: no cover - recovery path
                logger.exception("Rider %s failed to move; resetting route",
                                 getattr(r, "rider_id", "?"))
                r.route = []
        check_consistency()
    return globalvar.get_value("tick")


class SystemManager:
    """Facade around the global system state."""

    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        return globalvar.get_value("riders", [])

    @property
    def rider_id_counter(self):
        return globalvar.get_value("rider_id_counter", 0)

    @property
    def running(self):
        return bool(globalvar.get_value("running", False))

    @property
    def current_tick(self):
        return globalvar.get_value("tick", 0)

    @property
    def recruitment_cost(self):
        return globalvar.get_value("recruitment_cost", 0)

    def recruit_rider(self, force=False):
        return recruit_rider(force)

    def advance(self, ticks=1):
        return advance_time(ticks)

    def stop(self):
        globalvar.set_value("running", False)

    def check_consistency(self):
        return check_consistency()
