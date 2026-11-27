"""System manager: funds, rider recruitment, simulation ticks and persistence."""

import json
import logging
import math
import os

import globalvar
from order import OrderManager, find_best_rider_for_order
from path_planner import GridMap, PathPlanner
from rider import IDLE, Rider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "recruit_threshold": 300,
    "recruit_cost": 300,
    "rider_speed": 10,
    "rider_start_x": 435,
    "rider_start_y": 385,
}


def load_config(path):
    """Load system parameters from a JSON configuration file.

    The file may either be a flat object of parameters or an object with a
    ``"parameters"`` key. Unknown keys and non-integer values are ignored.

    Args:
        path: Path to the JSON file.

    Returns:
        Dictionary of recognised parameters; empty if the file is missing or
        invalid.
    """
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Could not read config %s: %s", path, exc)
        return {}
    if not isinstance(data, dict):
        logger.error("Config %s must contain a JSON object", path)
        return {}
    params = data.get("parameters", data)
    result = {}
    for key, value in params.items():
        if key not in DEFAULT_CONFIG:
            continue
        if isinstance(value, bool) or not isinstance(value, int):
            logger.warning("Ignoring non-integer config value %s=%r",
                           key, value)
            continue
        result[key] = value
    return result


class SystemManager:
    """Core coordinator for funds, riders, orders and simulated time.

    Attributes:
        config: Effective system parameters.
        funds: Current system funds (may be negative after manual edits).
        rider_id_counter: Last issued rider ID.
        is_running: Main loop control flag.
        current_time: Current simulated tick.
        grid_map: The 8x8 :class:`GridMap`.
        planner: The :class:`PathPlanner` used for route previews.
        order_manager: The :class:`OrderManager` owning all orders.
    """

    def __init__(self, config=None):
        """Create the manager with default or supplied parameters.

        Args:
            config: Optional dictionary overriding DEFAULT_CONFIG keys.
        """
        self.config = dict(DEFAULT_CONFIG)
        for key, value in (config or {}).items():
            if key in DEFAULT_CONFIG:
                self.config[key] = value
        self.funds = int(self.config["initial_funds"])
        self.rider_id_counter = 0
        self.is_running = True
        self.current_time = 0
        self.grid_map = GridMap()
        self.planner = PathPlanner(self.grid_map)
        self.order_manager = OrderManager()
        if globalvar.get_value("riders") is None:
            globalvar.set_value("riders", [])
        self._publish_time()

    @property
    def riders(self):
        """Return the global rider list (``list[Rider]``)."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    def _publish_time(self):
        """Copy the current tick into the global store."""
        globalvar.set_value("current_time", self.current_time)

    def get_rider(self, rider_id):
        """Return the rider with ``rider_id`` or None.

        Args:
            rider_id: Identifier to look up.

        Returns:
            The matching :class:`Rider` or None.
        """
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def idle_riders(self):
        """Return riders whose state is idle."""
        return [r for r in self.riders if r.state == IDLE]

    def recruit_rider(self):
        """Recruit a new rider if funds allow.

        Returns:
            The new :class:`Rider`, or None if funds are insufficient.
        """
        cost = self.config["recruit_cost"]
        if self.funds < cost:
            logger.info("Recruitment skipped: funds %d below cost %d",
                        self.funds, cost)
            return None
        self.funds -= cost
        self.rider_id_counter += 1
        rider = Rider(
            self.rider_id_counter,
            x=self.config["rider_start_x"],
            y=self.config["rider_start_y"],
            speed=self.config["rider_speed"],
        )
        self.riders.append(rider)
        logger.info("Recruited rider %d (funds now %d)",
                    rider.rider_id, self.funds)
        return rider

    def _ensure_capacity(self):
        """Recruit riders while pending orders outnumber idle riders.

        Recruitment requires funds of at least ``recruit_threshold``.

        Returns:
            Number of riders recruited.
        """
        recruited = 0
        threshold = self.config["recruit_threshold"]
        while (len(self.order_manager.pending) > len(self.idle_riders())
               and self.funds >= threshold):
            if self.recruit_rider() is None:
                break
            recruited += 1
        return recruited

    def dispatch_pending(self):
        """Assign every pending order to its best rider.

        Returns:
            List of ``(order, rider)`` pairs assigned in this call.
        """
        assigned = []
        for order in list(self.order_manager.pending):
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            self.order_manager.assign_order(order, rider)
            assigned.append((order, rider))
        return assigned

    def submit_order(self, res_pos, cus_pos):
        """Create an order, recruit if needed and dispatch it.

        Args:
            res_pos: Restaurant position ``[x, y]``.
            cus_pos: Customer position ``[x, y]``.

        Returns:
            Tuple ``(order, rider, new_rider_added)``. ``rider`` is None if
            no rider could be assigned.
        """
        order = self.order_manager.create_order(res_pos, cus_pos,
                                                self.current_time)
        recruited = self._ensure_capacity()
        self.dispatch_pending()
        rider = self.get_rider(order.rider_id) if order.rider_id else None
        return order, rider, recruited > 0

    def tick(self):
        """Advance the simulation by one tick.

        Increments the clock, moves every rider, checks state consistency and
        dispatches any pending orders.
        """
        self.current_time += 1
        self._publish_time()
        for rider in list(self.riders):
            rider.move()
        self.check_consistency()
        self._ensure_capacity()
        self.dispatch_pending()

    def check_consistency(self):
        """Detect and repair inconsistent order/rider bookkeeping.

        Orders that reference a missing rider are returned to the pending
        queue.

        Returns:
            Number of repairs performed.
        """
        repairs = 0
        rider_ids = {r.rider_id for r in self.riders}
        for order in self.order_manager.active_orders():
            if order.rider_id is None:
                continue
            holder = self.get_rider(order.rider_id)
            if holder is None or order not in holder.orders:
                logger.warning("Order %d lost its rider %s; requeueing",
                               order.id, order.rider_id)
                order.rider_id = None
                order.set_status(order.PENDING)
                if order not in self.order_manager.pending:
                    self.order_manager.pending.append(order)
                repairs += 1
        for rider in self.riders:
            if rider.orders and rider.rider_id not in rider_ids:
                repairs += 1
        return repairs

    def preview_route(self, start, restaurant, customer, speed):
        """Compute the combined pickup and delivery route for display.

        Args:
            start: Starting position ``(x, y)``.
            restaurant: Restaurant cell centre ``(x, y)``.
            customer: Customer cell centre ``(x, y)``.
            speed: Movement speed in units per tick.

        Returns:
            Tuple ``(segments, total_distance, estimated_time)``.
        """
        leg_one = self.planner.plan(start, restaurant, speed)
        leg_two = self.planner.plan(restaurant, customer, speed)
        segments = leg_one.segments + leg_two.segments
        total = leg_one.total_distance + leg_two.total_distance
        estimated = math.ceil(total / speed) if speed > 0 and total > 0 else 0
        return segments, total, estimated

    def status_snapshot(self):
        """Return a dictionary describing the current system state.

        Returns:
            Dictionary with time, funds, rider counts, pending orders and
            per-rider details.
        """
        riders = self.riders
        return {
            "time": self.current_time,
            "funds": self.funds,
            "rider_count": len(riders),
            "idle": len(self.idle_riders()),
            "pending": self.order_manager.pending_count(),
            "riders": [r.to_dict() for r in riders],
        }

    def to_dict(self):
        """Return the full persistable state of the system.

        Returns:
            JSON-serialisable dictionary with parameters, system values,
            riders and order history.
        """
        return {
            "parameters": dict(self.config),
            "system": {
                "funds": self.funds,
                "rider_id_counter": self.rider_id_counter,
                "current_time": self.current_time,
            },
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.orders],
        }

    def save_state(self, path):
        """Write the system state to a JSON file.

        Args:
            path: Destination file path.

        Returns:
            The path written.

        Raises:
            OSError: If the file cannot be written.
        """
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
        logger.info("State saved to %s", path)
        return path


def init_system(config=None):
    """Initialise global variables and create the system manager.

    Args:
        config: Optional parameter overrides (see DEFAULT_CONFIG).

    Returns:
        The initialised :class:`SystemManager`.
    """
    globalvar._init()
    globalvar.set_value("riders", [])
    system = SystemManager(config)
    logger.info("System initialised with funds %d", system.funds)
    return system
