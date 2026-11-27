"""System management: funds, rider recruitment, simulated time and dispatch."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from globalvar import DEFAULT_CONFIG, get_value, set_value
from order import find_best_rider_for_order
from order_model import Order
from path_planner import PathPlanner
from rider import STATE_IDLE, Rider

logger = logging.getLogger(__name__)


def load_config(path: str) -> Dict[str, Any]:
    """Load system parameters from a JSON configuration file.

    Recognised keys: initial_funds, recruit_cost, recruit_fund_threshold,
    max_run_ticks. Each must be a non-negative integer.

    Args:
        path: Path to the JSON file containing a single object.

    Returns:
        A copy of the active configuration after applying the file.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the content is malformed.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("configuration file must contain a JSON object")

    config = get_value("config")
    for key in DEFAULT_CONFIG:
        if key not in data:
            continue
        value = data[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"invalid value for '{key}': {value!r}")
        config[key] = value
    if "initial_funds" in data:
        set_value("funds", config["initial_funds"])
    logger.info("Loaded configuration from %s", path)
    return dict(config)


def init_system(config_path: Optional[str] = None) -> "SystemManager":
    """Initialise global state and return the system manager.

    Args:
        config_path: Optional JSON configuration file. Missing or invalid
            files fall back to the built-in defaults.

    Returns:
        A ready-to-use SystemManager.
    """
    globalvar._init()
    if config_path and os.path.exists(config_path):
        try:
            load_config(config_path)
        except (OSError, ValueError) as exc:
            logger.error("Failed to load config %s (%s); using defaults",
                         config_path, exc)
            globalvar._init()
    return SystemManager()


class SystemManager:
    """Facade over the global simulation state.

    Responsible for funds, the rider list, rider recruitment, the tick
    loop and dispatching pending orders.
    """

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------
    def _cfg(self, key: str) -> int:
        return int(get_value("config")[key])

    @property
    def funds(self) -> int:
        """System funds (may be negative)."""
        return int(get_value("funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        set_value("funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """The dynamic list of riders."""
        return get_value("riders")

    @property
    def rider_id_counter(self) -> int:
        """Last rider id issued."""
        return int(get_value("rider_id_counter", 0))

    @property
    def is_running(self) -> bool:
        """Main loop control flag."""
        return bool(get_value("is_running", True))

    @is_running.setter
    def is_running(self, value: bool) -> None:
        set_value("is_running", bool(value))

    @property
    def tick_count(self) -> int:
        """Current simulated time in ticks."""
        return int(get_value("tick", 0))

    @property
    def orders(self) -> List[Order]:
        """All orders ever created in this session."""
        return get_value("orders")

    @property
    def pending_orders(self) -> List[Order]:
        """Orders waiting for a rider."""
        return get_value("pending_orders")

    # ------------------------------------------------------------------
    # Riders
    # ------------------------------------------------------------------
    def idle_rider_count(self) -> int:
        """Number of riders that are idle and have no assigned orders."""
        return sum(1 for r in self.riders
                   if r.state == STATE_IDLE and not r.orders)

    def recruit_rider(self) -> Rider:
        """Create a new rider and deduct the recruitment cost.

        Returns:
            The newly created Rider.
        """
        counter = self.rider_id_counter + 1
        set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        self.funds = self.funds - self._cfg("recruit_cost")
        logger.info("Recruited rider %s (funds now %s)", counter, self.funds)
        return rider

    def try_recruit(self, pending_count: int) -> bool:
        """Recruit riders while funds allow and pending orders exceed idle riders.

        Args:
            pending_count: Number of orders waiting for assignment.

        Returns:
            True if at least one rider was added.
        """
        added = False
        idle = self.idle_rider_count()
        while (self.funds >= self._cfg("recruit_fund_threshold")
               and pending_count > idle):
            self.recruit_rider()
            idle += 1
            added = True
        return added

    def rider_for_order(self, order: Order) -> Optional[Rider]:
        """Return the rider currently responsible for ``order``, if any."""
        for rider in self.riders:
            if rider.rider_id == order.rider_id:
                return rider
        return None

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    def submit_order(
        self, res_pos: Tuple[int, int], cus_pos: Tuple[int, int]
    ) -> Tuple[Order, Optional[Rider], bool]:
        """Create an order, recruit if needed, and dispatch it.

        Args:
            res_pos: Restaurant coordinates (x, y), 0-800.
            cus_pos: Customer coordinates (x, y), 0-800.

        Returns:
            Tuple (order, assigned_rider_or_None, new_rider_added).
        """
        order = Order(res_pos, cus_pos, start_time=self.tick_count)
        self.orders.append(order)
        self.pending_orders.append(order)
        added = self.try_recruit(len(self.pending_orders))
        self.dispatch_pending()
        return order, self.rider_for_order(order), added

    def dispatch_pending(self) -> int:
        """Assign every pending order to its best rider.

        Returns:
            Number of orders assigned during this call.
        """
        assigned = 0
        for order in list(self.pending_orders):
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            rider.orders.append(order)
            order.assign_to(rider.rider_id)
            order.route = PathPlanner.build_route(
                rider.position, [order.restaurant_pos, order.customer_pos]
            )
            self.pending_orders.remove(order)
            assigned += 1
            logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return assigned

    # ------------------------------------------------------------------
    # Time
    # ------------------------------------------------------------------
    def tick(self) -> None:
        """Advance simulated time by one unit and move every rider.

        Exceptions raised by an individual rider are logged and the rider
        is reset to a consistent state, so the simulation keeps running.
        """
        set_value("tick", self.tick_count + 1)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive recovery
                logger.exception("Rider %s failed during move; recovering",
                                 rider.rider_id)
                rider.path = []
                if not rider.orders:
                    rider.state = STATE_IDLE
        self.dispatch_pending()

    def run_until_order_complete(self, order: Order,
                                 max_ticks: Optional[int] = None) -> int:
        """Run ticks until ``order`` is delivered.

        Args:
            order: The order to follow.
            max_ticks: Safety bound on the number of ticks.

        Returns:
            Number of ticks elapsed.

        Raises:
            RuntimeError: If the order is not completed within ``max_ticks``.
        """
        limit = max_ticks if max_ticks is not None else self._cfg("max_run_ticks")
        start = self.tick_count
        while order.status != "completed":
            if self.tick_count - start >= limit:
                raise RuntimeError(
                    f"order {order.id} not completed within {limit} ticks")
            self.tick()
        return self.tick_count - start

    # ------------------------------------------------------------------
    # Consistency and persistence
    # ------------------------------------------------------------------
    def check_consistency(self) -> List[str]:
        """Return a list of detected state inconsistencies (empty if none)."""
        issues: List[str] = []
        ids = [r.rider_id for r in self.riders]
        if len(set(ids)) != len(ids):
            issues.append("duplicate rider ids detected")
        for rider in self.riders:
            if rider.state != STATE_IDLE and not rider.orders:
                issues.append(f"rider {rider.rider_id} is busy without orders")
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    issues.append(
                        f"order {order.id} mismatched with rider {rider.rider_id}")
                if order.status == "completed":
                    issues.append(
                        f"completed order {order.id} still held by rider "
                        f"{rider.rider_id}")
            if not (0 <= rider.x <= 800 and 0 <= rider.y <= 800):
                issues.append(f"rider {rider.rider_id} outside map")
        return issues

    def save_state(self, path: str) -> None:
        """Persist parameters, riders and order history as JSON.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        data = {
            "funds": self.funds,
            "tick": self.tick_count,
            "rider_id_counter": self.rider_id_counter,
            "config": dict(get_value("config")),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.orders],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("Saved simulation state to %s", path)
