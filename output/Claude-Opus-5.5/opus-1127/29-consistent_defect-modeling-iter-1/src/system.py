"""System initialisation and the SystemManager core class."""

import logging

import globalvar
from rider import Rider, DEFAULT_SPEED

logger = logging.getLogger(__name__)

DEFAULT_FUNDS = 1000
RECRUITMENT_COST = 500
RECRUITMENT_THRESHOLD = 300


def init_system(config=None):
    """Initialise all global system parameters.

    ``config`` may be a dict of overrides (see :mod:`config`).
    Returns a :class:`SystemManager`.
    """
    config = config or {}
    globalvar._init()
    globalvar.set_value("funds", int(config.get("initial_funds", DEFAULT_FUNDS)))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)
    globalvar.set_value("rider_speed", int(config.get("rider_speed", DEFAULT_SPEED)))
    globalvar.set_value("recruitment_cost",
                        int(config.get("recruitment_cost", RECRUITMENT_COST)))
    globalvar.set_value("recruitment_threshold",
                        int(config.get("recruitment_threshold", RECRUITMENT_THRESHOLD)))
    return SystemManager()


def create_rider(charge=True):
    """Create a rider, register it and (optionally) deduct the cost."""
    counter = globalvar.get_value("rider_id_counter")
    counter = (counter if isinstance(counter, int) else 0) + 1
    globalvar.set_value("rider_id_counter", counter)
    rider = Rider(counter)
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    riders.append(rider)
    if charge:
        funds = globalvar.get_value("funds")
        if not isinstance(funds, int):
            funds = DEFAULT_FUNDS
        cost = globalvar.get_value("recruitment_cost") or RECRUITMENT_COST
        globalvar.set_value("funds", funds - cost)
    logger.info("Recruited rider %d", rider.rider_id)
    return rider


class SystemManager:
    """Manages funds, riders, time and system state."""

    @property
    def funds(self):
        """Current funds."""
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        """All riders."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def rider_id_counter(self):
        """Last assigned rider id."""
        return globalvar.get_value("rider_id_counter", 0)

    @property
    def running(self):
        """Main loop flag."""
        return bool(globalvar.get_value("running", False))

    @running.setter
    def running(self, value):
        globalvar.set_value("running", bool(value))

    @property
    def current_tick(self):
        """Current simulated time."""
        return globalvar.get_value("tick", 0)

    @property
    def recruitment_cost(self):
        """Cost of one rider."""
        return globalvar.get_value("recruitment_cost", RECRUITMENT_COST)

    @property
    def recruitment_threshold(self):
        """Minimum funds to recruit."""
        return globalvar.get_value("recruitment_threshold", RECRUITMENT_THRESHOLD)

    def idle_riders(self):
        """Riders without any work."""
        return [r for r in self.riders if r.is_idle()]

    def pending_order_count(self):
        """Number of unassigned orders."""
        return sum(1 for o in (globalvar.get_value("orders") or [])
                   if o.status == "pending")

    def check_recruitment(self):
        """Recruit a rider if funds >= threshold and pending > idle riders.

        Returns the new rider or None.
        """
        if (self.funds >= self.recruitment_threshold
                and self.pending_order_count() > len(self.idle_riders())):
            return create_rider()
        return None

    def advance(self, ticks=1):
        """Advance the simulation by ``ticks`` time units."""
        for _ in range(max(0, int(ticks))):
            globalvar.set_value("tick", self.current_tick + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception:  # keep simulation alive
                    logger.exception("Rider %s failed to move; resetting",
                                     rider.rider_id)
                    rider.path = []
                    rider._path_target = None

    def consistency_check(self):
        """Return a list of detected inconsistencies (and repair them)."""
        problems = []
        ids = [r.rider_id for r in self.riders]
        if len(ids) != len(set(ids)):
            problems.append("duplicate rider ids")
        for r in self.riders:
            if r.state not in (0, 1, 2):
                problems.append("rider %s invalid state %s" % (r.rider_id, r.state))
                r.state = 0
                r.current_order = None
        return problems

    def snapshot(self):
        """Serialisable state of the whole system."""
        return {
            "funds": self.funds,
            "tick": self.current_tick,
            "rider_id_counter": self.rider_id_counter,
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in (globalvar.get_value("orders") or [])],
        }
