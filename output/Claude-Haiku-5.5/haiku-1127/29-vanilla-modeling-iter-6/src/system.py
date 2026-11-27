"""System manager: funds, riders, recruitment, ticks and state persistence."""

import json
import logging
from dataclasses import asdict

import globalvar
from config import Configuration
from display import DisplayManager
from grid_map import GridMap
from order import OrderManager
from path_planner import PathPlanner
from rider import STATE_IDLE, STATE_PICKING_UP, Rider

logger = logging.getLogger(__name__)


class SystemManager:
    """Coordinates riders, orders, funds and the simulation clock.

    Attributes:
        config: Configuration parameters.
        funds: Current system funds (may become negative).
        rider_id_counter: Last issued rider id.
        is_running: Main loop control flag.
        current_tick: Number of simulated ticks so far.
        grid_map: The 8x8 grid model.
        planner: Shared PathPlanner.
        order_manager: OrderManager instance.
        display: DisplayManager instance.
    """

    def __init__(self, config=None):
        """Create the system with the given configuration.

        Args:
            config: Optional Configuration; defaults are used when omitted.
        """
        self.config = config or Configuration()
        self.funds = int(self.config.initial_funds)
        self.rider_id_counter = 0
        self.is_running = True
        self.current_tick = 0
        self.grid_map = GridMap()
        self.planner = PathPlanner(self.grid_map)
        self.order_manager = OrderManager()
        self.display = DisplayManager()
        if globalvar.get_value("riders") is None:
            globalvar.set_value("riders", [])
        globalvar.set_value("current_tick", self.current_tick)

    @property
    def riders(self):
        """The live list of riders stored in the global variable store."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    def idle_riders(self):
        """Return riders that are idle and have no assigned orders."""
        return [rider for rider in self.riders
                if rider.state == STATE_IDLE and not rider.orders]

    def find_rider(self, rider_id):
        """Return the rider with ``rider_id`` or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def recruit_rider(self):
        """Create a new rider, deducting the recruitment cost.

        Returns:
            The newly created Rider.
        """
        self.rider_id_counter += 1
        rider = Rider(self.rider_id_counter,
                      self.config.initial_rider_x,
                      self.config.initial_rider_y,
                      self.config.initial_rider_speed)
        self.funds -= self.config.rider_recruitment_cost
        self.riders.append(rider)
        logger.info("Recruited rider %d; funds now %d", rider.rider_id,
                    self.funds)
        return rider

    def maybe_recruit(self):
        """Recruit riders while pending orders exceed idle riders.

        Recruitment requires funds of at least the configured threshold.

        Returns:
            List of riders recruited during this call.
        """
        new_riders = []
        idle = len(self.idle_riders())
        while (self.order_manager.pending_count() > idle
               and self.funds >= self.config.recruitment_fund_threshold):
            new_riders.append(self.recruit_rider())
            idle += 1
        return new_riders

    def submit_order(self, restaurant_pos, customer_pos):
        """Create an order, recruit if needed and assign it.

        Args:
            restaurant_pos: (x, y) restaurant coordinates.
            customer_pos: (x, y) customer coordinates.

        Returns:
            Tuple (order, added) where ``added`` is True when a new rider
            was recruited for this order.
        """
        order = self.order_manager.create_order(restaurant_pos, customer_pos)
        added = bool(self.maybe_recruit())
        self.order_manager.assign_pending()
        return order, added

    def tick(self):
        """Advance the whole simulation by one tick.

        Order: update the clock, recruit and assign pending orders, then move
        every rider. Exceptions in one rider are logged and do not stop the
        others.
        """
        self.current_tick += 1
        globalvar.set_value("current_tick", self.current_tick)
        try:
            self.maybe_recruit()
            self.order_manager.assign_pending()
        except Exception:
            logger.exception("Error while dispatching pending orders")
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:
                logger.exception("Error while moving rider %d",
                                 rider.rider_id)
                rider.resync()

    def run_until_order_done(self, order, max_ticks=None):
        """Run ticks until ``order`` is delivered or the limit is reached.

        Args:
            order: The Order to monitor.
            max_ticks: Maximum ticks to simulate; defaults to configuration.

        Returns:
            True if the order was completed.
        """
        limit = max_ticks or self.config.max_ticks_per_order
        for _ in range(limit):
            if order.status == "completed":
                return True
            self.tick()
        return order.status == "completed"

    def check_consistency(self):
        """Return a list of human-readable consistency problems.

        Problems are detected without modifying state.
        """
        problems = []
        for rider in self.riders:
            if rider.state != STATE_IDLE and not rider.orders:
                problems.append(f"rider {rider.rider_id} is busy without "
                                "orders")
            if rider.state == STATE_PICKING_UP and rider.orders:
                if rider.orders[0].status == "completed":
                    problems.append(f"rider {rider.rider_id} holds a "
                                    "completed order")
        return problems

    def repair_state(self):
        """Repair inconsistent rider states and return the number of fixes."""
        fixes = 0
        for rider in self.riders:
            before = len(rider.orders)
            rider.orders = [order for order in rider.orders
                            if order.status != "completed"]
            if len(rider.orders) != before:
                fixes += 1
            if rider.resync():
                fixes += 1
        if fixes:
            logger.warning("Repaired %d inconsistent rider state(s)", fixes)
        return fixes

    def to_dict(self):
        """Return a JSON-serialisable snapshot of the whole system."""
        return {
            "tick": self.current_tick,
            "funds": self.funds,
            "rider_id_counter": self.rider_id_counter,
            "config": asdict(self.config),
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict()
                       for order in self.order_manager.orders],
        }

    def save_state(self, path):
        """Write the system snapshot to a JSON file.

        Args:
            path: Destination file path.

        Returns:
            True on success, False if the file could not be written.
        """
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self.to_dict(), handle, indent=2)
            logger.info("State saved to %s", path)
            return True
        except OSError as exc:
            logger.error("Could not save state to %s: %s", path, exc)
            return False


def init_system(config_path=None):
    """Initialise the global store and create the system manager.

    Sets funds to the configured initial value (default 1000), an empty rider
    list, rider id counter 0, running state True and tick 0.

    Args:
        config_path: Optional path to a JSON configuration file.

    Returns:
        The initialised SystemManager.
    """
    globalvar._init()
    config = Configuration.load(config_path) if config_path else Configuration()
    system = SystemManager(config)
    logger.info("System initialised with funds %d", system.funds)
    return system
