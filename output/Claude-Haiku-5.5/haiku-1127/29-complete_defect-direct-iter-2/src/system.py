"""System-level management: funds, rider recruitment and time advancement.

``SystemManager`` coordinates riders, orders and funds. ``init_system``
prepares the global state and returns a ready-to-use manager.
"""

import json
import logging

import globalvar
from config import SETTINGS
from order import OrderManager
from order_model import STATUS_COMPLETED, STATUS_PENDING
from rider import IDLE, STATE_NAMES, Rider

logger = logging.getLogger(__name__)


class SystemManager:
    """Core manager for funds, riders, orders and simulated time.

    Attributes:
        order_manager: The :class:`order.OrderManager` handling orders.
    """

    def __init__(self):
        """Create a manager with a fresh order manager."""
        self.order_manager = OrderManager()

    @property
    def funds(self):
        """Current system fund balance (integer, may be negative)."""
        return globalvar.get_value("funds")

    @property
    def tick(self):
        """Current simulated time in ticks."""
        return globalvar.get_value("tick")

    @property
    def riders(self):
        """The dynamic list of riders."""
        return globalvar.get_value("riders")

    @property
    def orders(self):
        """History list of every order ever created."""
        return globalvar.get_value("orders")

    def add_funds(self, amount):
        """Add an integer amount to the fund balance.

        Args:
            amount: Integer amount; may be negative.
        """
        globalvar.set_value("funds", self.funds + int(amount))

    def get_rider(self, rider_id):
        """Find a rider by identifier.

        Args:
            rider_id: The rider's unique identifier.

        Returns:
            The matching Rider, or None if not found.
        """
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def recruit_if_needed(self):
        """Create a new rider when funds reach the hiring threshold.

        The hiring cost is deducted from the funds when a rider is created.

        Returns:
            The newly created Rider, or None if no rider was added.
        """
        if self.funds < SETTINGS["rider_hire_threshold"]:
            return None
        counter = (globalvar.get_value("rider_id_counter") or 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        globalvar.set_value("funds",
                            self.funds - SETTINGS["rider_hire_cost"])
        logger.info("Recruited rider #%d", counter)
        return rider

    def submit_order(self, res_pos, cus_pos):
        """Recruit if funds allow, then create and assign an order.

        Args:
            res_pos: Restaurant coordinates as ``(x, y)`` integers.
            cus_pos: Customer coordinates as ``(x, y)`` integers.

        Returns:
            A tuple ``(order, new_rider)`` where ``new_rider`` is the Rider
            recruited during this call or None.
        """
        new_rider = self.recruit_if_needed()
        order = self.order_manager.submit(res_pos, cus_pos)
        return order, new_rider

    def advance(self, ticks=1):
        """Advance the simulation by one or more ticks.

        Each tick moves every rider, retries pending order assignments,
        checks recruitment and collects completed orders. A rider that
        raises an exception is reset and its orders are re-queued.

        Args:
            ticks: Number of ticks to simulate (at least 1).

        Returns:
            List of IDs of orders completed during the advance.

        Raises:
            ValueError: If ``ticks`` is less than 1.
        """
        if ticks < 1:
            raise ValueError("tick count must be at least 1")
        completed_ids = []
        for _ in range(ticks):
            globalvar.set_value("tick", self.tick + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception:  # pylint: disable=broad-except
                    logger.exception("Rider #%d failed; resetting",
                                     rider.rider_id)
                    self._reset_rider(rider)
            self.order_manager.assign_pending()
            self.recruit_if_needed()
            completed_ids.extend(
                order.id for order in self.order_manager.collect_completed())
        return completed_ids

    def _reset_rider(self, rider):
        """Return a rider to idle and re-queue its unfinished orders.

        Args:
            rider: The Rider to reset.
        """
        pending = globalvar.get_value("pending_orders")
        for order in rider.orders:
            if order.status == STATUS_COMPLETED:
                continue
            order.status = STATUS_PENDING
            order.rider_id = None
            if order not in pending:
                pending.append(order)
        rider.orders = []
        rider.path = []
        rider.state = IDLE
        rider.special_case = False
        rider.wait_ticks = 0
        logger.warning("Rider #%d reset to idle", rider.rider_id)

    @staticmethod
    def _rider_problems(rider):
        """List the consistency problems found for one rider.

        Args:
            rider: The Rider to inspect.

        Returns:
            List of human-readable problem descriptions (empty if none).
        """
        problems = []
        if rider.state not in STATE_NAMES:
            problems.append(f"rider #{rider.rider_id} has invalid state "
                            f"{rider.state}")
        if rider.state == IDLE and rider.path:
            problems.append(f"rider #{rider.rider_id} is idle but has a route")
        if rider.state != IDLE and not rider.orders:
            problems.append(f"rider #{rider.rider_id} is busy without orders")
        for order in rider.orders:
            if order.status == STATUS_COMPLETED:
                problems.append(f"rider #{rider.rider_id} holds completed "
                                f"order #{order.id}")
            if order.rider_id != rider.rider_id:
                problems.append(f"order #{order.id} is not linked to rider "
                                f"#{rider.rider_id}")
        return problems

    def check_consistency(self):
        """Run system state consistency checks.

        Returns:
            List of problem descriptions. An empty list means consistent.
        """
        issues = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)
            issues.extend(self._rider_problems(rider))
        if not isinstance(self.funds, int):
            issues.append("fund balance is not an integer")
        return issues

    def recover(self):
        """Repair inconsistent riders and report what was found.

        Returns:
            List of problem descriptions detected before repair.
        """
        issues = self.check_consistency()
        for rider in list(self.riders):
            if self._rider_problems(rider):
                self._reset_rider(rider)
        if issues:
            logger.warning("Recovered from %d consistency issue(s)",
                           len(issues))
        return issues

    def save_state(self, path):
        """Write a JSON snapshot of settings, riders and orders to a file.

        Args:
            path: Destination file path.

        Returns:
            The path that was written.

        Raises:
            OSError: If the file cannot be written.
        """
        data = {
            "settings": dict(SETTINGS),
            "funds": self.funds,
            "tick": self.tick,
            "rider_id_counter": globalvar.get_value("rider_id_counter"),
            "order_id_counter": globalvar.get_value("order_id_counter"),
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.orders],
            "pending_order_ids": [
                order.id for order in globalvar.get_value("pending_orders")
            ],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("State saved to %s", path)
        return path


def init_system():
    """Initialise global state and create the system manager.

    Resets the global store, sets the starting funds and recruits the
    first rider if the funds meet the hiring threshold.

    Returns:
        A ready-to-use SystemManager instance.
    """
    globalvar._init()  # pylint: disable=protected-access
    globalvar.set_value("funds", SETTINGS["initial_funds"])
    manager = SystemManager()
    manager.recruit_if_needed()
    logger.info("System initialised with funds=%s", manager.funds)
    return manager
