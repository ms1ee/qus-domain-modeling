"""System manager: funds, rider recruitment, simulation ticks and persistence."""

import json
import logging
import math
import os
from typing import Any, Dict, Optional

import globalvar
from globalvar import DEFAULT_PARAMETERS, get_value, set_value
from order import OrderManager
from order_model import STATUS_COMPLETED, Order
from path_planner import GridMap, PathPlanner, Route
from rider import STATE_IDLE, STATE_PICKING_UP, Rider

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"
STATE_FILE = "system_state.json"
POSITIVE_PARAMETERS = ("rider_speed", "max_orders_per_rider", "max_ticks_per_order")


class SystemManager:
    """Owns funds, riders, orders and the simulated clock."""

    def __init__(self) -> None:
        """Create the system components and recruit the first rider if funded."""
        set_value("riders", get_value("riders") or [])
        self.grid_map = GridMap()
        self.planner = PathPlanner()
        self.order_manager = OrderManager()
        self.check_recruitment()

    # ------------------------------------------------------------------
    # Properties backed by the global store
    # ------------------------------------------------------------------
    @property
    def funds(self) -> int:
        """Current system fund balance (may be negative)."""
        return int(get_value("funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        set_value("funds", int(value))

    @property
    def riders(self) -> list:
        """List of all riders."""
        return get_value("riders") or []

    @property
    def rider_id_counter(self) -> int:
        """Last issued rider identifier."""
        return int(get_value("rider_id_counter", 0))

    @property
    def current_tick(self) -> int:
        """Current simulated tick."""
        return int(get_value("current_tick", 0))

    @property
    def is_running(self) -> bool:
        """Whether the main loop should keep running."""
        return bool(get_value("is_running", True))

    @is_running.setter
    def is_running(self, value: bool) -> None:
        set_value("is_running", bool(value))

    # ------------------------------------------------------------------
    # Rider management
    # ------------------------------------------------------------------
    def create_rider(self) -> Rider:
        """Create a new idle rider with a unique identifier.

        Returns:
            The newly created rider.
        """
        new_id = self.rider_id_counter + 1
        set_value("rider_id_counter", new_id)
        rider = Rider(new_id)
        self.riders.append(rider)
        logger.info("Recruited rider %s", new_id)
        return rider

    def check_recruitment(self) -> bool:
        """Recruit a rider when funds reach the recruitment threshold.

        The recruitment cost is deducted from the funds.

        Returns:
            True if a rider was added, otherwise False.
        """
        threshold = int(get_value("recruit_threshold", 300))
        if self.funds >= threshold:
            self.funds = self.funds - int(get_value("recruit_cost", 300))
            self.create_rider()
            return True
        return False

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    def submit_order(self, res_pos, cus_pos) -> Dict[str, Any]:
        """Create an order, assign it and plan its route.

        Args:
            res_pos: Restaurant ``[x, y]`` (0-800).
            cus_pos: Customer ``[x, y]`` (0-800).

        Returns:
            Dictionary with keys ``order``, ``rider`` (or None), ``new_rider``,
            ``route`` (or None) and ``estimated_ticks`` (or None).

        Raises:
            ValueError: If a coordinate is invalid.
        """
        new_rider = self.check_recruitment()
        order = self.order_manager.create_order(res_pos, cus_pos, self.current_tick)
        rider = self.order_manager.assign(order)
        route: Optional[Route] = None
        estimated: Optional[int] = None
        if rider is not None:
            route = self.planner.build_route(
                (rider.x, rider.y), order.res_center, order.cus_center
            )
            estimated = math.ceil(route.total_distance / rider.speed) if rider.speed else None
        return {
            "order": order,
            "rider": rider,
            "new_rider": new_rider,
            "route": route,
            "estimated_ticks": estimated,
        }

    def run_until_complete(self, order: Order, max_ticks: Optional[int] = None) -> int:
        """Advance the simulation until the order is delivered.

        Args:
            order: Order to wait for.
            max_ticks: Maximum number of ticks to simulate.

        Returns:
            Number of ticks simulated.
        """
        limit = max_ticks or int(get_value("max_ticks_per_order", 10000))
        start = self.current_tick
        while order.status != STATUS_COMPLETED and self.current_tick - start < limit:
            self.tick()
        if order.status != STATUS_COMPLETED:
            logger.warning("Order %s not completed within %s ticks", order.id, limit)
        return self.current_tick - start

    # ------------------------------------------------------------------
    # Simulation clock
    # ------------------------------------------------------------------
    def tick(self) -> None:
        """Advance the simulation by one tick.

        Recruits riders if funded, retries pending orders, and moves every
        rider. Exceptions raised by one rider are logged and that rider is
        reset to a consistent state so the rest of the system keeps running.
        """
        set_value("current_tick", self.current_tick + 1)
        self.check_recruitment()
        self.order_manager.retry_pending()
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # noqa: BLE001 - recovery path
                logger.exception("Rider %s failed during tick; recovering", rider.rider_id)
                self._recover_rider(rider)

    @staticmethod
    def _recover_rider(rider: Rider) -> None:
        """Restore a rider to a consistent state after an unexpected error."""
        rider.path = []
        rider.stall_count = 0
        rider.special_case = False
        if not rider.orders:
            rider.state = STATE_IDLE
        elif rider.state == STATE_IDLE:
            rider.state = STATE_PICKING_UP

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save_state(self, path: str = STATE_FILE) -> None:
        """Write parameters, riders and order history to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        state = {
            "parameters": {k: get_value(k) for k in DEFAULT_PARAMETERS},
            "funds": self.funds,
            "current_tick": self.current_tick,
            "rider_id_counter": self.rider_id_counter,
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.orders],
        }
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
        os.replace(tmp_path, path)
        logger.info("System state saved to %s", path)


def load_config(path: str = CONFIG_FILE) -> bool:
    """Load system parameters from a JSON configuration file.

    The file may contain a ``parameters`` object or the parameters at top
    level. Unknown keys and invalid values are ignored with a warning.

    Args:
        path: Configuration file path.

    Returns:
        True if the file was read, otherwise False.
    """
    if not os.path.exists(path):
        logger.info("No configuration file at %s; using defaults", path)
        return False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Could not read configuration %s: %s", path, exc)
        return False
    if not isinstance(data, dict):
        logger.error("Configuration %s must contain a JSON object", path)
        return False
    params = data.get("parameters", data)
    if not isinstance(params, dict):
        return False
    for key in DEFAULT_PARAMETERS:
        if key not in params:
            continue
        try:
            value = int(params[key])
        except (TypeError, ValueError):
            logger.warning("Parameter %s has an invalid value; ignored", key)
            continue
        if value < 0 or (key in POSITIVE_PARAMETERS and value == 0):
            logger.warning("Parameter %s out of range; ignored", key)
            continue
        set_value(key, value)
    return True


def init_system() -> SystemManager:
    """Initialise global state, load configuration and build the system.

    Returns:
        A ready-to-use :class:`SystemManager`.
    """
    globalvar._init()
    load_config(CONFIG_FILE)
    set_value("funds", int(get_value("initial_funds", 300)))
    system = SystemManager()
    logger.info("System initialised with %s rider(s)", len(system.riders))
    return system
