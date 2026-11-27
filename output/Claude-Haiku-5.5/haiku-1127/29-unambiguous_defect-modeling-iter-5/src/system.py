"""System-level coordination: funds, rider recruitment, ticks and persistence."""

import json
import logging

import globalvar
from order import OrderManager, find_best_rider_for_order
from order_model import STATUS_COMPLETED
from path_planner import PathPlanner, MAP_SIZE, GRID_SIZE
from rider import Rider, IDLE, PICKING_UP, DELIVERING

logger = logging.getLogger(__name__)

DEFAULT_FUNDS = 1000
DEFAULT_RECRUITMENT_COST = 200
DEFAULT_MAX_RIDERS = 20
DELIVERY_FEE = 30
OPERATING_COST_PER_BUSY_RIDER = 1


class SystemManager:
    """Core manager for funds, riders, orders and the simulated clock.

    Attributes:
        funds (int): Current system balance (may be negative).
        rider_id_counter (int): Last assigned rider ID.
        is_running (bool): Controls the main loop.
        simulated_time (int): Number of elapsed ticks.
        rider_recruitment_cost (int): Cost deducted per recruited rider.
        max_riders (int): Maximum number of riders that may be recruited.
        planner (PathPlanner): Shared path planner.
        order_manager (OrderManager): Order creation and tracking.
        riders (list[Rider]): The rider list, shared with the global store.
    """

    def __init__(self, funds=DEFAULT_FUNDS,
                 recruitment_cost=DEFAULT_RECRUITMENT_COST,
                 max_riders=DEFAULT_MAX_RIDERS):
        """Create the system manager.

        Args:
            funds: Initial system funds.
            recruitment_cost: Cost of recruiting one rider.
            max_riders: Maximum number of riders allowed.
        """
        self.funds = int(funds)
        self.rider_id_counter = 0
        self.is_running = True
        self.simulated_time = 0
        self.rider_recruitment_cost = int(recruitment_cost)
        self.max_riders = int(max_riders)
        self.planner = PathPlanner()
        self.order_manager = OrderManager()
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        self.riders = riders
        globalvar.set_value("simulated_time", self.simulated_time)

    # ------------------------------------------------------------------
    # Rider management
    # ------------------------------------------------------------------
    def has_idle_rider(self):
        """Return True if at least one rider is idle with no orders."""
        return any(r.state == IDLE and not r.orders for r in self.riders)

    def can_recruit(self):
        """Return True if a new rider can be recruited now."""
        return (len(self.riders) < self.max_riders
                and self.funds >= self.rider_recruitment_cost)

    def recruit_rider(self):
        """Recruit a new rider if funds and capacity allow.

        Returns:
            The new :class:`Rider`, or ``None`` if recruitment is not possible.
        """
        if not self.can_recruit():
            return None
        self.rider_id_counter += 1
        self.funds -= self.rider_recruitment_cost
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        logger.info("Recruited rider %d", rider.rider_id)
        return rider

    def get_rider(self, rider_id):
        """Return the rider with ``rider_id`` or ``None``."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    # ------------------------------------------------------------------
    # Order handling
    # ------------------------------------------------------------------
    def submit_order(self, restaurant_pos, customer_pos):
        """Create an order and assign it to the best available rider.

        A new rider is recruited when no idle rider exists or no rider can
        accept the order and funds allow recruitment.

        Args:
            restaurant_pos: Restaurant point ``[x, y]`` (0..800).
            customer_pos: Customer point ``[x, y]`` (0..800).

        Returns:
            Dictionary with keys ``order``, ``assigned``, ``new_rider``,
            ``rider``, ``route`` (list of waypoints), ``speed``,
            ``estimated_time`` and ``reason``.
        """
        order = self.order_manager.create_order(
            restaurant_pos, customer_pos, self.simulated_time)

        new_rider = False
        rider = find_best_rider_for_order(order)
        if rider is None or not self.has_idle_rider():
            recruited = self.recruit_rider()
            if recruited is not None:
                new_rider = True
                rider = find_best_rider_for_order(order)

        if rider is None:
            return {
                "order": order,
                "assigned": False,
                "new_rider": False,
                "rider": None,
                "route": [],
                "speed": 0,
                "estimated_time": 0,
                "reason": "no rider available and recruitment is not possible",
            }

        to_restaurant = self.planner.plan(rider.position, order.restaurant_pos,
                                          rider.speed)
        to_customer = self.planner.plan(order.restaurant_pos, order.customer_pos,
                                        rider.speed)
        route = to_restaurant.waypoints + to_customer.waypoints[1:]
        total = to_restaurant.total_distance + to_customer.total_distance
        estimated = -(-total // rider.speed)

        self.order_manager.assign_order(order, rider)
        return {
            "order": order,
            "assigned": True,
            "new_rider": new_rider,
            "rider": rider,
            "route": route,
            "speed": rider.speed,
            "estimated_time": estimated,
            "reason": "",
        }

    def active_orders(self):
        """Return all orders that are not yet completed."""
        return [o for o in self.order_manager.orders
                if o.status != STATUS_COMPLETED]

    # ------------------------------------------------------------------
    # Simulation clock
    # ------------------------------------------------------------------
    def tick(self):
        """Advance the simulation by one unit of time.

        Every rider moves once. Completed deliveries pay a fee and busy riders
        incur an operating cost. Errors in a single rider are logged and the
        system state is repaired without stopping the simulation.

        Returns:
            Net income generated during this tick.
        """
        self.simulated_time += 1
        globalvar.set_value("simulated_time", self.simulated_time)
        income = 0
        cost = 0
        for rider in list(self.riders):
            busy = rider.state != IDLE
            try:
                completed = rider.move()
            except Exception:  # error recovery: keep the simulation running
                logger.exception("Rider %s failed during tick", rider.rider_id)
                self.verify_consistency()
                continue
            income += DELIVERY_FEE * len(completed)
            if busy:
                cost += OPERATING_COST_PER_BUSY_RIDER
        self.funds += income - cost
        return income - cost

    def run_ticks(self, count):
        """Advance the simulation by ``count`` ticks.

        Args:
            count: Number of ticks to simulate (non-negative).

        Returns:
            Net income accumulated over all ticks.
        """
        total = 0
        for _ in range(count):
            total += self.tick()
        return total

    def stop(self):
        """Stop the main simulation loop."""
        self.is_running = False
        globalvar.set_value("is_running", False)

    # ------------------------------------------------------------------
    # Consistency and persistence
    # ------------------------------------------------------------------
    def verify_consistency(self):
        """Check and repair the state of all riders.

        Returns:
            List of human-readable descriptions of repaired issues.
        """
        issues = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)

            if not self.planner.is_valid_point(rider.x, rider.y):
                rider.x, rider.y = self.planner.snap(rider.x, rider.y)
                rider.reset_navigation()
                issues.append(f"rider {rider.rider_id} moved back into the map")
            elif not self.planner.is_on_street(rider.x, rider.y):
                rider.x, rider.y = self.planner.snap(rider.x, rider.y)
                rider.reset_navigation()
                issues.append(f"rider {rider.rider_id} snapped onto a street")

            finished = [o for o in rider.orders if o.status == STATUS_COMPLETED]
            if finished:
                rider.orders[:] = [o for o in rider.orders
                                   if o.status != STATUS_COMPLETED]
                issues.append(f"rider {rider.rider_id} removed completed orders")

            if rider.state in (PICKING_UP, DELIVERING) and not rider.orders:
                rider.state = IDLE
                rider.reset_navigation()
                issues.append(f"rider {rider.rider_id} reset to idle")
        for issue in issues:
            logger.warning("Consistency repair: %s", issue)
        return issues

    def snapshot(self):
        """Return a JSON-serializable snapshot of the whole system."""
        return {
            "funds": self.funds,
            "simulated_time": self.simulated_time,
            "rider_id_counter": self.rider_id_counter,
            "rider_recruitment_cost": self.rider_recruitment_cost,
            "max_riders": self.max_riders,
            "riders": [
                dict(r.summary(), log=r.log) for r in self.riders
            ],
            "orders": [o.to_dict() for o in self.order_manager.orders],
        }

    def save_snapshot(self, path):
        """Write the system snapshot to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.snapshot(), handle, indent=2)


def load_config(path):
    """Load system parameters from a JSON configuration file.

    Args:
        path: Path to the JSON file.

    Returns:
        Dictionary of parameters, empty if the file is missing or invalid.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not load configuration %s: %s", path, exc)
        return {}
    if not isinstance(data, dict):
        logger.warning("Configuration %s must contain a JSON object", path)
        return {}
    return data


def init_system(config_path=None):
    """Initialize global state and create the system manager.

    Args:
        config_path: Optional JSON configuration file with keys
            ``initial_funds``, ``rider_recruitment_cost`` and ``max_riders``.

    Returns:
        The initialized :class:`SystemManager`.
    """
    globalvar._init()
    config = load_config(config_path) if config_path else {}
    globalvar.set_value("riders", [])
    manager = SystemManager(
        funds=config.get("initial_funds", DEFAULT_FUNDS),
        recruitment_cost=config.get("rider_recruitment_cost",
                                    DEFAULT_RECRUITMENT_COST),
        max_riders=config.get("max_riders", DEFAULT_MAX_RIDERS),
    )
    globalvar.set_value("system", manager)
    globalvar.set_value("is_running", True)
    return manager
