"""System initialization and resource management.

Provides :class:`SystemManager`, which manages system funds, the rider pool,
automatic rider recruitment, order dispatch and the simulated clock.
"""

import logging

import globalvar
from config import SETTINGS
from order import OrderManager
from order_model import STATUS_COMPLETED
from rider import Rider, STATE_IDLE

logger = logging.getLogger(__name__)


class SystemManager:
    """Core manager for funds, riders, recruitment and the simulation clock.

    Attributes:
        order_manager: The OrderManager used for order creation and assignment.
    """

    def __init__(self):
        """Create the manager and its order manager."""
        self.order_manager = OrderManager()

    # ------------------------------------------------------------------ #
    # Global state accessors
    # ------------------------------------------------------------------ #
    @property
    def funds(self):
        """int: Current system funds."""
        return globalvar.get_value("funds")

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", int(value))

    @property
    def riders(self):
        """list[Rider]: The dynamic rider list."""
        return globalvar.get_value("riders")

    @property
    def tick_count(self):
        """int: Current simulated time."""
        return globalvar.get_value("tick") or 0

    @property
    def running(self):
        """bool: Whether the main loop should keep running."""
        return bool(globalvar.get_value("running"))

    def shutdown(self):
        """Stop the main loop."""
        globalvar.set_value("running", False)
        logger.info("System shutdown requested at tick %d", self.tick_count)

    def next_rider_id(self):
        """Issue the next unique rider ID.

        Returns:
            int: A rider ID that has not been used before in this session.
        """
        counter = (globalvar.get_value("rider_id_counter") or 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        return counter

    # ------------------------------------------------------------------ #
    # Counts and recruitment
    # ------------------------------------------------------------------ #
    def idle_count(self):
        """Return the number of riders with state idle.

        Returns:
            int: Number of idle riders.
        """
        return sum(1 for rider in self.riders if rider.state == STATE_IDLE)

    def pending_count(self):
        """Return the number of orders waiting for assignment.

        Returns:
            int: Number of pending orders.
        """
        return len(self.order_manager.pending_orders())

    def can_recruit(self):
        """Check whether funds allow recruiting a new rider.

        Returns:
            bool: True if funds meet the recruitment threshold and cost.
        """
        return (
            self.funds >= SETTINGS["recruit_funds_threshold"]
            and self.funds >= SETTINGS["recruit_cost"]
        )

    def recruit_rider(self):
        """Create a new rider and charge the recruitment cost.

        Returns:
            Rider: The newly recruited rider.

        Raises:
            RuntimeError: If funds are insufficient.
        """
        cost = SETTINGS["recruit_cost"]
        if self.funds < cost:
            raise RuntimeError(
                f"Insufficient funds to recruit a rider (funds {self.funds}, "
                f"cost {cost})."
            )
        self.funds = self.funds - cost
        rider = Rider(self.next_rider_id())
        self.riders.append(rider)
        logger.info(
            "Recruited rider #%d at tick %d (funds now %d)",
            rider.rider_id, self.tick_count, self.funds,
        )
        return rider

    def maybe_recruit(self):
        """Recruit a rider if pending orders exceed idle riders and funds allow.

        Returns:
            Rider or None: The new rider, or None if no recruitment happened.
        """
        if self.pending_count() > self.idle_count() and self.can_recruit():
            return self.recruit_rider()
        return None

    # ------------------------------------------------------------------ #
    # Dispatch and clock
    # ------------------------------------------------------------------ #
    def dispatch_pending(self):
        """Assign every pending order to its closest rider.

        Recruitment is considered before each assignment.

        Returns:
            list[tuple]: ``(order, rider, recruited)`` for each assignment,
            where ``recruited`` tells whether a rider was recruited for it.
        """
        results = []
        for order in self.order_manager.pending_orders():
            recruited = self.maybe_recruit() is not None
            if not self.riders:
                break
            rider = self.order_manager.assign(order)
            results.append((order, rider, recruited))
        return results

    def submit_order(self, coords):
        """Create an order from raw coordinates and dispatch it immediately.

        Args:
            coords: Sequence ``[restaurant_x, restaurant_y, customer_x,
                customer_y]`` of integers in the range 0-800.

        Returns:
            tuple: ``(order, rider, recruited)``. ``rider`` is None when no
            rider could be assigned; the order then stays pending.
        """
        order = self.order_manager.create_order(coords)
        results = self.dispatch_pending()
        for dispatched, rider, recruited in results:
            if dispatched is order:
                return order, rider, recruited
        return order, None, False

    def tick(self):
        """Advance the simulation by one tick.

        Increments the clock, retries pending order dispatch and moves every
        rider one step.

        Returns:
            int: The new tick value.
        """
        globalvar.set_value("tick", self.tick_count + 1)
        self.dispatch_pending()
        for rider in list(self.riders):
            rider.move()
        completed = sum(
            1 for order in self.order_manager.all_orders()
            if order.status == STATUS_COMPLETED
        )
        logger.debug("Tick %d complete (%d completed orders)",
                     self.tick_count, completed)
        return self.tick_count

    def check_consistency(self):
        """Verify system state and repair recoverable inconsistencies.

        Returns:
            list[str]: Descriptions of every issue found and repaired.
        """
        issues = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)
            if rider.repair_state():
                issues.append(
                    f"rider #{rider.rider_id} state repaired "
                    f"(state {rider.state}, {len(rider.orders)} orders)"
                )
        if not isinstance(self.funds, int):
            globalvar.set_value("funds", SETTINGS["initial_funds"])
            issues.append("system funds were invalid and reset")
        return issues


def init_system():
    """Initialize global state and return the system manager.

    Sets funds to the initial value, an empty rider list, the rider ID counter
    to 0, the running state to True and the clock to 0.

    Returns:
        SystemManager: The initialized system manager.
    """
    globalvar._init()
    globalvar.set_value("funds", SETTINGS["initial_funds"])
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    logger.info("System initialized with funds %d", SETTINGS["initial_funds"])
    return SystemManager()
