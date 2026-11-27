"""System manager: funds, rider recruitment, simulation clock and persistence."""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from order import MAX_ORDERS_PER_RIDER, OrderManager
from order_model import Order
from rider import IDLE, Rider

logger = logging.getLogger(__name__)

INITIAL_FUNDS = 2000
RECRUITMENT_COST = 500
MAX_RIDERS = 20
DEFAULT_SAVE_PATH = "dispatch_state.json"


class SystemManager:
    """Owns the system funds, the rider list and the simulation clock.

    Attributes:
        recruitment_cost: Funds deducted for each new rider.
        max_riders: Upper bound on the number of riders.
        order_manager: The OrderManager for this session.
    """

    def __init__(self, initial_funds: int = INITIAL_FUNDS,
                 recruitment_cost: int = RECRUITMENT_COST,
                 max_riders: int = MAX_RIDERS) -> None:
        globalvar.set_value("funds", int(initial_funds))
        globalvar.set_value("riders", [])
        globalvar.set_value("rider_id_counter", 0)
        globalvar.set_value("is_running", True)
        globalvar.set_value("current_tick", 0)
        self.recruitment_cost = int(recruitment_cost)
        self.max_riders = int(max_riders)
        self.order_manager = OrderManager()

    # ----- global state accessors -------------------------------------
    @property
    def funds(self) -> int:
        """System fund balance (may be negative)."""
        return int(globalvar.get_value("funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        globalvar.set_value("funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """The dynamic list of riders."""
        return globalvar.get_value("riders", [])

    @property
    def rider_id_counter(self) -> int:
        """Last rider ID handed out."""
        return int(globalvar.get_value("rider_id_counter", 0))

    @rider_id_counter.setter
    def rider_id_counter(self, value: int) -> None:
        globalvar.set_value("rider_id_counter", int(value))

    @property
    def is_running(self) -> bool:
        """Main loop control flag."""
        return bool(globalvar.get_value("is_running", True))

    @is_running.setter
    def is_running(self, value: bool) -> None:
        globalvar.set_value("is_running", bool(value))

    @property
    def current_tick(self) -> int:
        """Current simulated time."""
        return int(globalvar.get_value("current_tick", 0))

    @current_tick.setter
    def current_tick(self, value: int) -> None:
        globalvar.set_value("current_tick", int(value))

    # ----- rider management -------------------------------------------
    def recruit_rider(self) -> Optional[Rider]:
        """Create a new rider if funds and the rider cap allow it.

        Returns:
            The new Rider, or None if recruitment was not possible.
        """
        if len(self.riders) >= self.max_riders:
            logger.info("Recruitment skipped: rider cap %s reached", self.max_riders)
            return None
        if self.funds < self.recruitment_cost:
            logger.info("Recruitment skipped: insufficient funds (%s)", self.funds)
            return None
        self.funds = self.funds - self.recruitment_cost
        self.rider_id_counter = self.rider_id_counter + 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        logger.info("Recruited rider #%s", rider.rider_id)
        return rider

    def has_free_rider(self) -> bool:
        """Return True if at least one rider has no orders."""
        return any(not rider.orders for rider in self.riders)

    def has_available_capacity(self) -> bool:
        """Return True if at least one rider can accept another order."""
        return any(len(r.orders) < MAX_ORDERS_PER_RIDER for r in self.riders)

    def dispatch_order(self, order: Order) -> Tuple[Optional[Rider], bool]:
        """Assign an order, recruiting a rider first if none is free.

        Args:
            order: The order to dispatch.

        Returns:
            Tuple ``(rider, added)``. ``rider`` is the assigned Rider or None
            if the order could not be placed. ``added`` is True if a new rider
            was recruited for this order.
        """
        added = False
        if not self.has_free_rider():
            added = self.recruit_rider() is not None
        rider = self.order_manager.assign_order(order)
        return rider, added

    def create_order(self, restaurant_x: int, restaurant_y: int,
                     customer_x: int, customer_y: int) -> Order:
        """Create an order through the OrderManager.

        Raises:
            ValueError: If any coordinate is invalid.
        """
        return self.order_manager.create_order(restaurant_x, restaurant_y,
                                               customer_x, customer_y)

    # ----- simulation -------------------------------------------------
    def tick(self) -> None:
        """Advance the simulation by one tick and move every rider."""
        self.current_tick = self.current_tick + 1
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # keep the simulation alive on rider faults
                logger.exception("Rider #%s failed to move; state reset", rider.rider_id)
                rider.state = IDLE
                rider.path.clear()
                rider.target = None

    # ----- consistency and persistence --------------------------------
    def check_consistency(self, repair: bool = True) -> List[str]:
        """Check the rider and order state for inconsistencies.

        Args:
            repair: When True, fix problems that can be repaired automatically.

        Returns:
            Human-readable descriptions of the problems found.
        """
        problems: List[str] = []
        seen_ids = set()
        for rider in list(self.riders):
            if rider.rider_id in seen_ids:
                problems.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)

            for order in list(rider.orders):
                if order.status == "completed":
                    problems.append(
                        f"completed order #{order.id} still held by rider #{rider.rider_id}")
                    if repair:
                        rider.orders.remove(order)
                elif order.rider_id != rider.rider_id:
                    problems.append(
                        f"order #{order.id} is held by rider #{rider.rider_id} "
                        f"but assigned to rider #{order.rider_id}")
                    if repair:
                        rider.orders.remove(order)

            if not rider.orders and rider.state != IDLE:
                problems.append(f"rider #{rider.rider_id} has no orders but state is {rider.state_name}")
                if repair:
                    rider.state = IDLE
                    rider.path.clear()
                    rider.target = None
                    rider.special_case = False

        if self.funds < 0:
            problems.append(f"system funds are negative ({self.funds})")
        return problems

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the system state."""
        return {
            "config": {
                "recruitment_cost": self.recruitment_cost,
                "max_riders": self.max_riders,
            },
            "funds": self.funds,
            "current_tick": self.current_tick,
            "rider_id_counter": self.rider_id_counter,
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.order_manager.orders],
        }

    def save(self, path: str) -> None:
        """Write the system snapshot to a JSON file.

        Raises:
            OSError: If the file cannot be written.
        """
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
        logger.info("System state saved to %s", path)

    def apply_config(self, config: Dict[str, Any]) -> None:
        """Apply system parameters from a configuration dictionary.

        Recognised keys: ``initial_funds``, ``recruitment_cost``, ``max_riders``.

        Raises:
            ValueError: If a value is not a non-negative integer.
        """
        if "initial_funds" in config:
            self.funds = _non_negative_int(config["initial_funds"], "initial_funds")
        if "recruitment_cost" in config:
            self.recruitment_cost = _non_negative_int(config["recruitment_cost"],
                                                      "recruitment_cost")
        if "max_riders" in config:
            self.max_riders = _non_negative_int(config["max_riders"], "max_riders")


def _non_negative_int(value: Any, name: str) -> int:
    """Convert a configuration value to a non-negative integer."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"config '{name}' must be an integer") from None
    if number < 0:
        raise ValueError(f"config '{name}' must not be negative")
    return number


def load_config(path: str) -> Dict[str, Any]:
    """Load a JSON configuration file.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the file is not a valid JSON object.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("configuration file must contain a JSON object")
    return data


def init_system() -> SystemManager:
    """Initialise global variables and return a ready SystemManager."""
    globalvar._init()
    return SystemManager()
