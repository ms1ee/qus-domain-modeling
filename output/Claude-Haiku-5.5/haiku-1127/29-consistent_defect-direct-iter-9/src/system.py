"""System-level management: funds, rider roster, recruitment, and ticks."""

import logging

import globalvar
from rider import DEFAULT_SPEED, IDLE, Rider

logger = logging.getLogger("dispatch.system")


def init_system():
    """Initialise global variables to their startup defaults."""
    globalvar._init()
    logger.info("System initialised with funds=%s", globalvar.get_value("funds"))


class SystemManager:
    """Manages system funds, the rider roster, recruitment and simulation ticks."""

    def get_funds(self):
        """Return the current system fund balance."""
        return globalvar.get_value("funds")

    def adjust_funds(self, delta):
        """Add ``delta`` (may be negative) to the fund balance.

        Returns:
            The new fund balance.
        """
        new_value = int(globalvar.get_value("funds")) + int(delta)
        globalvar.set_value("funds", new_value)
        return new_value

    def idle_rider_count(self):
        """Return the number of riders in the idle state."""
        return sum(1 for rider in globalvar.get_value("riders") if rider.state == IDLE)

    def add_rider(self):
        """Create a new rider at (400, 400) and add it to the roster.

        Returns:
            The newly created Rider.
        """
        counter = globalvar.get_value("rider_id_counter") + 1
        globalvar.set_value("rider_id_counter", counter)
        speed = globalvar.get_value("rider_speed", DEFAULT_SPEED)
        rider = Rider(counter, speed=speed)
        globalvar.get_value("riders").append(rider)
        return rider

    def maybe_recruit(self, pending_count):
        """Recruit a rider when funds and demand allow it.

        A rider is created when funds are at least the recruit threshold and
        the number of pending orders exceeds the number of idle riders. The
        recruit cost is deducted from the funds.

        Args:
            pending_count: Number of orders waiting for a rider.

        Returns:
            The new Rider, or None if no rider was recruited.
        """
        min_funds = globalvar.get_value("recruit_min_funds", 300)
        cost = globalvar.get_value("recruit_cost", 500)
        if self.get_funds() >= min_funds and pending_count > self.idle_rider_count():
            self.adjust_funds(-cost)
            rider = self.add_rider()
            logger.info("Recruited rider #%s (cost %s)", rider.rider_id, cost)
            return rider
        return None

    def remove_rider(self, rider_id):
        """Remove an idle rider that has no unfinished orders.

        Returns:
            True if the rider was removed, otherwise False.
        """
        riders = globalvar.get_value("riders")
        for rider in riders:
            if rider.rider_id == rider_id:
                if rider.state != IDLE or rider.active_order_count() > 0:
                    return False
                riders.remove(rider)
                logger.info("Removed rider #%s", rider_id)
                return True
        return False

    def tick(self):
        """Advance simulated time by one tick and move every rider.

        Returns:
            The new simulation time.
        """
        new_time = globalvar.get_value("time", 0) + 1
        globalvar.set_value("time", new_time)
        for rider in list(globalvar.get_value("riders")):
            rider.move()
        return new_time

    def is_running(self):
        """Return the main loop running flag."""
        return bool(globalvar.get_value("running"))

    def stop(self):
        """Request that the main loop terminate."""
        globalvar.set_value("running", False)

    def check_consistency(self):
        """Check internal state for inconsistencies.

        Returns:
            List of human-readable issue descriptions (empty when healthy).
        """
        issues = []
        funds = globalvar.get_value("funds")
        if not isinstance(funds, int):
            issues.append("system funds is not an integer")
        riders = globalvar.get_value("riders")
        ids = [rider.rider_id for rider in riders]
        if len(ids) != len(set(ids)):
            issues.append("duplicate rider ids detected")
        if ids and max(ids) > globalvar.get_value("rider_id_counter"):
            issues.append("rider id counter is behind existing rider ids")
        for rider in riders:
            active = rider.active_order_count()
            if (rider.state == IDLE) != (active == 0):
                issues.append(
                    f"rider #{rider.rider_id} state {rider.state} inconsistent "
                    f"with {active} active order(s)"
                )
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    issues.append(
                        f"order #{order.id} listed under rider #{rider.rider_id} "
                        f"but assigned to #{order.rider_id}"
                    )
        for order in globalvar.get_value("pending_orders"):
            if order.status != "pending":
                issues.append(f"pending order #{order.id} has status {order.status}")
        return issues
