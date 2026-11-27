"""System initialisation, funds, rider recruitment and state persistence."""

import json
import logging

import globalvar
from order_model import Order
from path_planner import CELL_SIZE, GRID_CELLS
from rider import IDLE, Rider

logger = logging.getLogger(__name__)

INITIAL_FUNDS = 1000
RECRUIT_MIN_FUNDS = 300
RECRUIT_COST = 500
STATE_FORMAT_VERSION = 1


def build_grid_map():
    """Build the 8x8 grid map.

    Returns:
        list[list[tuple[int, int]]]: ``grid[row][col]`` is the top-left
        ``(x, y)`` corner of that cell.
    """
    return [[(col * CELL_SIZE, row * CELL_SIZE) for col in range(GRID_CELLS)]
            for row in range(GRID_CELLS)]


def init_system():
    """Initialise all global parameters for a fresh simulation.

    Returns:
        None
    """
    globalvar._init()
    globalvar.set_value("funds", INITIAL_FUNDS)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("grid_map", build_grid_map())
    Order.set_next_id(1)
    logger.info("System initialised with funds=%d", INITIAL_FUNDS)


class SystemManager:
    """Facade over global system state: funds, riders, ticks and recruitment.

    All methods are static and operate on the values held in ``globalvar``.
    """

    @staticmethod
    def get_funds():
        """Return the current system funds."""
        return globalvar.get_value("funds")

    @staticmethod
    def add_funds(amount):
        """Add ``amount`` (may be negative) to system funds.

        Args:
            amount: Integer amount to add.

        Returns:
            int: New fund balance.
        """
        new_value = SystemManager.get_funds() + int(amount)
        globalvar.set_value("funds", new_value)
        return new_value

    @staticmethod
    def get_riders():
        """Return the list of riders (the live list object)."""
        return globalvar.get_value("riders")

    @staticmethod
    def find_rider(rider_id):
        """Return the rider with ``rider_id`` or None.

        Args:
            rider_id: Identifier to look up.

        Returns:
            Rider or None.
        """
        return next((r for r in SystemManager.get_riders()
                     if r.rider_id == rider_id), None)

    @staticmethod
    def idle_rider_count():
        """Return the number of riders with no active orders."""
        return sum(1 for r in SystemManager.get_riders()
                   if not r.has_active_orders())

    @staticmethod
    def create_rider():
        """Recruit a new rider at (400, 400), deducting the recruit cost.

        Returns:
            Rider: The newly created rider.
        """
        counter = (globalvar.get_value("rider_id_counter") or 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        SystemManager.get_riders().append(rider)
        SystemManager.add_funds(-RECRUIT_COST)
        logger.info("Recruited rider #%d (funds now %s)", counter,
                    SystemManager.get_funds())
        return rider

    @staticmethod
    def maybe_recruit(pending_count):
        """Recruit a rider when funds allow and demand exceeds idle riders.

        Args:
            pending_count: Number of pending (unassigned) orders.

        Returns:
            Rider or None: The new rider, or None if no recruitment happened.
        """
        funds = SystemManager.get_funds()
        idle = SystemManager.idle_rider_count()
        if funds >= RECRUIT_MIN_FUNDS and pending_count > idle:
            return SystemManager.create_rider()
        return None

    @staticmethod
    def remove_rider(rider_id):
        """Remove an idle rider from the system.

        Args:
            rider_id: Identifier of the rider to remove.

        Returns:
            bool: True if removed, False if not found or busy.
        """
        rider = SystemManager.find_rider(rider_id)
        if rider is None or rider.has_active_orders():
            return False
        SystemManager.get_riders().remove(rider)
        logger.info("Removed rider #%d", rider_id)
        return True

    @staticmethod
    def is_running():
        """Return the main loop running flag."""
        return bool(globalvar.get_value("running"))

    @staticmethod
    def stop():
        """Clear the running flag so the main loop exits."""
        globalvar.set_value("running", False)

    @staticmethod
    def current_tick():
        """Return the current simulated tick."""
        return globalvar.get_value("tick") or 0

    @staticmethod
    def tick():
        """Advance simulated time by one tick and move every rider.

        A failure in one rider is logged and does not stop the others.

        Returns:
            int: The new tick value.
        """
        new_tick = SystemManager.current_tick() + 1
        globalvar.set_value("tick", new_tick)
        for rider in list(SystemManager.get_riders()):
            try:
                rider.move()
            except Exception:  # error recovery: keep simulating
                logger.exception("Rider #%s failed during tick %d",
                                 rider.rider_id, new_tick)
        return new_tick

    @staticmethod
    def check_consistency():
        """Check internal state invariants.

        Returns:
            list[str]: Human-readable descriptions of any inconsistencies.
        """
        issues = []
        funds = SystemManager.get_funds()
        if not isinstance(funds, int):
            issues.append("system funds is not an integer")
        riders = SystemManager.get_riders()
        ids = [r.rider_id for r in riders]
        if len(set(ids)) != len(ids):
            issues.append("duplicate rider ids detected")
        for rider in riders:
            if rider.state == IDLE and rider.has_active_orders():
                issues.append(f"rider #{rider.rider_id} is idle but has "
                              "active orders")
            if rider.state != IDLE and rider.current_order is None:
                issues.append(f"rider #{rider.rider_id} is busy without a "
                              "current order")
        known_ids = set(ids)
        for order in globalvar.get_value("orders") or []:
            if order.status == "assigned" and order.rider_id not in known_ids:
                issues.append(f"order #{order.id} assigned to unknown rider")
        return issues

    @staticmethod
    def save_state(path):
        """Write system parameters, riders and order history to JSON.

        Args:
            path: Destination file path.

        Returns:
            str: The path written.
        """
        data = {
            "format_version": STATE_FORMAT_VERSION,
            "parameters": {
                "initial_funds": INITIAL_FUNDS,
                "recruit_min_funds": RECRUIT_MIN_FUNDS,
                "recruit_cost": RECRUIT_COST,
            },
            "funds": SystemManager.get_funds(),
            "rider_id_counter": globalvar.get_value("rider_id_counter"),
            "tick": SystemManager.current_tick(),
            "orders": [o.to_dict() for o in globalvar.get_value("orders")],
            "riders": [r.to_dict() for r in SystemManager.get_riders()],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("State saved to %s", path)
        return path

    @staticmethod
    def load_state(path):
        """Restore system state from a JSON file written by :meth:`save_state`.

        Args:
            path: Source file path.

        Returns:
            list[str]: Consistency issues found after loading.

        Raises:
            ValueError: If the file content is not valid state data.
            OSError: If the file cannot be read.
        """
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict) or "funds" not in data:
            raise ValueError("file does not contain a valid system state")
        orders = [Order.from_dict(item) for item in data.get("orders", [])]
        orders_by_id = {o.id: o for o in orders}
        riders = [Rider.from_dict(item, orders_by_id)
                  for item in data.get("riders", [])]
        Order.set_next_id(max(orders_by_id, default=0) + 1)
        globalvar.set_value("funds", int(data["funds"]))
        globalvar.set_value("rider_id_counter",
                            int(data.get("rider_id_counter", 0)))
        globalvar.set_value("tick", int(data.get("tick", 0)))
        globalvar.set_value("orders", orders)
        globalvar.set_value("riders", riders)
        issues = SystemManager.check_consistency()
        for issue in issues:
            logger.warning("Consistency issue after load: %s", issue)
        logger.info("State loaded from %s", path)
        return issues
