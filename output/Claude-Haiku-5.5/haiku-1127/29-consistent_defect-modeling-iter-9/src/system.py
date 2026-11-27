"""System-level state management: funds, rider recruitment and simulation loop."""

import json
import logging
from typing import List, Optional

from globalvar import _init, get_value, set_value
from order import OrderManager
from order_model import STATUS_COMPLETED
from rider import IDLE, Rider

logger = logging.getLogger("dispatch.system")

DEFAULT_INITIAL_FUNDS = 1000
DEFAULT_RECRUIT_THRESHOLD = 300
DEFAULT_RECRUIT_COST = 500
DEFAULT_MAX_TICKS_PER_ORDER = 1000


class SystemManager:
    """Owns funds, riders, orders and the simulation clock."""

    def __init__(self, recruit_threshold: int = DEFAULT_RECRUIT_THRESHOLD,
                 recruit_cost: int = DEFAULT_RECRUIT_COST,
                 max_ticks_per_order: int = DEFAULT_MAX_TICKS_PER_ORDER) -> None:
        """Create the system manager.

        Args:
            recruit_threshold: Minimum funds required to recruit a rider.
            recruit_cost: Funds deducted per recruited rider.
            max_ticks_per_order: Safety cap when simulating one order to completion.
        """
        self.order_manager = OrderManager()
        self.recruit_threshold = int(recruit_threshold)
        self.recruit_cost = int(recruit_cost)
        self.max_ticks_per_order = int(max_ticks_per_order)

    # ----- global state accessors -------------------------------------
    @property
    def funds(self) -> int:
        """System fund balance."""
        return get_value("funds")

    @funds.setter
    def funds(self, value: int) -> None:
        set_value("funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """Dynamic list of riders."""
        return get_value("riders")

    @property
    def rider_id_counter(self) -> int:
        """Last issued rider id."""
        return get_value("rider_id_counter")

    @rider_id_counter.setter
    def rider_id_counter(self, value: int) -> None:
        set_value("rider_id_counter", int(value))

    @property
    def is_running(self) -> bool:
        """Main loop control flag."""
        return get_value("is_running")

    @is_running.setter
    def is_running(self, value: bool) -> None:
        set_value("is_running", bool(value))

    @property
    def current_tick(self) -> int:
        """Simulated time."""
        return get_value("current_tick")

    @current_tick.setter
    def current_tick(self, value: int) -> None:
        set_value("current_tick", int(value))

    # ----- rider management -------------------------------------------
    def idle_rider_count(self) -> int:
        """Return the number of riders in the idle state."""
        return sum(1 for r in self.riders if r.state == IDLE)

    def create_rider(self) -> Rider:
        """Create and register a new rider with a unique id.

        Returns:
            The newly created Rider.
        """
        new_id = self.rider_id_counter + 1
        self.rider_id_counter = new_id
        rider = Rider(new_id)
        self.riders.append(rider)
        logger.info("Recruited rider %d", new_id)
        return rider

    def maybe_recruit(self, pending_count: int) -> Optional[Rider]:
        """Recruit a rider if funds allow and pending orders exceed idle riders.

        Args:
            pending_count: Number of orders waiting for a rider.

        Returns:
            The recruited Rider, or None.
        """
        if self.funds < self.recruit_threshold:
            return None
        if pending_count <= self.idle_rider_count():
            return None
        rider = self.create_rider()
        self.funds = self.funds - self.recruit_cost
        return rider

    def dispatch_pending(self) -> int:
        """Assign every pending order, recruiting riders when needed.

        Returns:
            Number of orders assigned during this call.
        """
        assigned = 0
        for order in list(self.order_manager.pending_orders()):
            pending = len(self.order_manager.pending_orders())
            self.maybe_recruit(pending)
            if self.order_manager.assign_order(order) is not None:
                assigned += 1
        return assigned

    # ----- order handling ----------------------------------------------
    def submit_order(self, restaurant_pos, customer_pos) -> dict:
        """Create an order and dispatch it.

        Args:
            restaurant_pos: Restaurant (x, y).
            customer_pos: Customer (x, y).

        Returns:
            Dict with keys "order", "rider", "recruited", "restaurant", "customer".
        """
        riders_before = len(self.riders)
        order = self.order_manager.create_order(restaurant_pos, customer_pos)
        self.dispatch_pending()
        rider = None
        if order.assigned_rider_id is not None:
            rider = next((r for r in self.riders if r.rider_id == order.assigned_rider_id), None)
        return {
            "order": order,
            "rider": rider,
            "recruited": len(self.riders) > riders_before,
            "restaurant": order.restaurant_pos,
            "customer": order.customer_pos,
        }

    # ----- simulation loop ----------------------------------------------
    def tick(self) -> None:
        """Advance the simulation by one unit of time."""
        self.current_tick = self.current_tick + 1
        self.dispatch_pending()
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # Error recovery: keep the simulation running.
                logger.exception("Rider %d failed during tick; resynchronising", rider.rider_id)
                rider.resynchronize()

    def run_until_complete(self, order, max_ticks: Optional[int] = None) -> int:
        """Advance time until the order is delivered or the cap is reached.

        Args:
            order: Order to watch.
            max_ticks: Optional override for the tick cap.

        Returns:
            Number of ticks simulated.
        """
        limit = self.max_ticks_per_order if max_ticks is None else int(max_ticks)
        ticks = 0
        while order.status != STATUS_COMPLETED and ticks < limit:
            self.tick()
            ticks += 1
        return ticks

    # ----- consistency and persistence ----------------------------------
    def check_consistency(self) -> List[str]:
        """Verify rider/order state consistency.

        Returns:
            List of human-readable problem descriptions (empty if healthy).
        """
        issues: List[str] = []
        for rider in self.riders:
            active = rider.active_orders()
            if rider.state == IDLE and active:
                issues.append(f"Rider {rider.rider_id} is idle but has active orders")
            if rider.state != IDLE and not active:
                issues.append(f"Rider {rider.rider_id} is busy without active orders")
            for order in rider.orders:
                if order.assigned_rider_id != rider.rider_id:
                    issues.append(f"Order {order.id} is held by rider {rider.rider_id} "
                                  f"but records rider {order.assigned_rider_id}")
        return issues

    def save_state(self, path: str) -> None:
        """Write system parameters, riders and order history to a JSON file.

        Args:
            path: Destination file path.
        """
        data = {
            "parameters": {
                "recruit_threshold": self.recruit_threshold,
                "recruit_cost": self.recruit_cost,
                "max_ticks_per_order": self.max_ticks_per_order,
            },
            "funds": self.funds,
            "current_tick": self.current_tick,
            "rider_id_counter": self.rider_id_counter,
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.orders],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("State saved to %s", path)


def load_config(path: str) -> dict:
    """Load a JSON configuration file.

    Args:
        path: Path to the configuration file.

    Returns:
        Parsed dictionary, or an empty dict if the file is missing or invalid.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        logger.warning("Configuration file %s not found; using defaults", path)
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Could not read configuration %s: %s", path, exc)
        return {}
    if not isinstance(data, dict):
        logger.error("Configuration %s must contain a JSON object", path)
        return {}
    return data


def init_system(config_path: Optional[str] = None) -> SystemManager:
    """Initialise global state and return a SystemManager.

    Startup defaults: funds 1000, empty rider list, rider id counter 0,
    running state True, tick 0. Values may be overridden by a JSON config
    file with keys initial_funds, recruit_threshold, recruit_cost,
    max_ticks_per_order.

    Args:
        config_path: Optional path to a JSON configuration file.

    Returns:
        The initialised SystemManager.
    """
    _init()
    config = load_config(config_path) if config_path else {}
    set_value("funds", int(config.get("initial_funds", DEFAULT_INITIAL_FUNDS)))
    set_value("riders", [])
    set_value("rider_id_counter", 0)
    set_value("is_running", True)
    set_value("current_tick", 0)
    return SystemManager(
        recruit_threshold=config.get("recruit_threshold", DEFAULT_RECRUIT_THRESHOLD),
        recruit_cost=config.get("recruit_cost", DEFAULT_RECRUIT_COST),
        max_ticks_per_order=config.get("max_ticks_per_order", DEFAULT_MAX_TICKS_PER_ORDER),
    )
