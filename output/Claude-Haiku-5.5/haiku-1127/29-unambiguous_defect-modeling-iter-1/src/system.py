"""System-level state management: funds, riders, clock and running flag."""

import logging

import config
import globalvar
from rider import Rider

logger = logging.getLogger(__name__)


def init_system():
    """Initialise global system state on startup.

    Sets funds, an empty rider list, the rider ID counter (0), the running
    flag (True), the simulated tick (0) and an empty order list.
    """
    globalvar._init()
    globalvar.set_value("funds", config.SETTINGS["initial_funds"])
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("is_running", True)
    globalvar.set_value("current_tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)
    logger.info("System initialised with funds=%s", config.SETTINGS["initial_funds"])


class SystemManager:
    """Facade over the global system state (funds, riders, clock, flags)."""

    @property
    def funds(self):
        """Current system fund balance (may be negative)."""
        return int(globalvar.get_value("funds") or 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", int(value))

    @property
    def rider_id_counter(self):
        """Last rider ID handed out."""
        return int(globalvar.get_value("rider_id_counter") or 0)

    @rider_id_counter.setter
    def rider_id_counter(self, value):
        globalvar.set_value("rider_id_counter", int(value))

    @property
    def is_running(self):
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("is_running"))

    def stop(self):
        """Request the main loop to terminate."""
        globalvar.set_value("is_running", False)

    @property
    def current_tick(self):
        """Simulated clock value."""
        return int(globalvar.get_value("current_tick") or 0)

    @current_tick.setter
    def current_tick(self, value):
        globalvar.set_value("current_tick", int(value))

    @property
    def recruitment_cost(self):
        """Cost deducted for each recruited rider."""
        return config.SETTINGS["recruitment_cost"]

    @property
    def riders(self):
        """The live list of riders (dynamic array, supports CRUD)."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    def get_rider(self, rider_id):
        """Return the rider with the given ID, or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def can_recruit(self):
        """Return True if funds and capacity allow recruiting a rider."""
        return (
            len(self.riders) < config.SETTINGS["max_riders"]
            and self.funds >= self.recruitment_cost
        )

    def recruit_rider(self):
        """Recruit a new rider if funds and capacity allow.

        Deducts the recruitment cost, increments the ID counter and appends
        the new rider to the rider list.

        Returns:
            The new Rider, or None if recruitment is not possible.
        """
        if len(self.riders) >= config.SETTINGS["max_riders"]:
            logger.warning("Rider capacity reached")
            return None
        if self.funds < self.recruitment_cost:
            logger.warning("Insufficient funds to recruit a rider")
            return None
        self.funds = self.funds - self.recruitment_cost
        self.rider_id_counter = self.rider_id_counter + 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        logger.info("Recruited rider %s", rider.rider_id)
        return rider

    def advance_tick(self):
        """Advance the simulation by one tick and move every rider.

        Errors raised by an individual rider are logged and do not stop the
        simulation, which keeps the system recoverable.

        Returns:
            The new tick value.
        """
        self.current_tick = self.current_tick + 1
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive recovery
                logger.exception("Rider %s failed during tick; resetting", rider.rider_id)
                rider.state = 0
                rider.special_case = False
        return self.current_tick
