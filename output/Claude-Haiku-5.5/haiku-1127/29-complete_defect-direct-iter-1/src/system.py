"""System initialization, funds management, rider recruitment and ticking."""

import logging

import config
import globalvar
from order import OrderManager
from rider import Rider

logger = logging.getLogger(__name__)


class SystemManager:
    """Manages system funds, the rider list and the simulation clock.

    State lives in the ``globalvar`` store, so instances are lightweight.
    """

    def __init__(self):
        """Create a manager bound to the global system state."""
        self.order_manager = OrderManager()

    # ------------------------------------------------------------------
    # Funds
    # ------------------------------------------------------------------
    def funds(self):
        """Return the current system fund balance (may be negative)."""
        return globalvar.get_value("funds", 0)

    def add_funds(self, amount):
        """Add (or subtract, for negative amounts) funds.

        Args:
            amount: Integer amount to add.

        Returns:
            int: The new balance.
        """
        new_value = self.funds() + int(amount)
        globalvar.set_value("funds", new_value)
        return new_value

    # ------------------------------------------------------------------
    # Riders (CRUD)
    # ------------------------------------------------------------------
    def riders(self):
        """Return a copy of the rider list."""
        return list(globalvar.get_value("riders", []) or [])

    def get_rider(self, rider_id):
        """Return the rider with the given ID, or None."""
        for rider in self.riders():
            if rider.rider_id == rider_id:
                return rider
        return None

    def recruit_rider(self):
        """Create a new idle rider, assign it an ID and pay the hiring cost.

        Returns:
            Rider: The newly recruited rider.
        """
        new_id = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", new_id)
        rider = Rider(new_id)
        globalvar.get_value("riders").append(rider)
        self.add_funds(-config.RIDER_COST)
        logger.info("Recruited rider %s", new_id)
        return rider

    def check_recruitment(self):
        """Recruit a rider automatically if funds reach the threshold.

        Returns:
            Rider or None: The new rider if one was recruited, else None.
        """
        if self.funds() >= config.RECRUIT_THRESHOLD:
            return self.recruit_rider()
        return None

    def remove_rider(self, rider_id):
        """Remove an idle rider that has no assigned orders.

        Args:
            rider_id: Identifier of the rider to remove.

        Returns:
            bool: True if the rider was removed.
        """
        rider = self.get_rider(rider_id)
        if rider is None or rider.orders:
            return False
        globalvar.get_value("riders").remove(rider)
        logger.info("Removed rider %s", rider_id)
        return True

    # ------------------------------------------------------------------
    # Simulation clock
    # ------------------------------------------------------------------
    def tick(self):
        """Advance the simulation by one tick.

        Order of operations: move all riders, check recruitment, retry
        pending orders.

        Returns:
            int: The new simulated tick value.
        """
        now = globalvar.get_value("tick", 0) + 1
        globalvar.set_value("tick", now)
        for rider in self.riders():
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive recovery
                logger.exception("Rider %s failed to move; resetting.",
                                 rider.rider_id)
                rider.orders = []
                rider.state = config.STATE_IDLE
                rider.path = []
        self.check_recruitment()
        self.order_manager.retry_pending()
        return now


def init_system():
    """Initialise global state and recruit the first rider if funds allow.

    Sets up the rider list (empty), rider ID counter (0), running state
    (True), funds, and the simulated tick (0).
    """
    globalvar._init()
    globalvar.set_value("funds", config.INITIAL_FUNDS)
    SystemManager().check_recruitment()
    logger.info("System initialised with funds=%s", globalvar.get_value("funds"))
