"""System-level management: initialisation, funds, recruitment, clock, and persistence."""

import json
import logging
import math
import os
import random
from typing import Any, Dict, List, Optional

import globalvar
from globalvar import get_value, next_id, set_value
from order import NoRiderAvailableError, OrderManager  # noqa: F401 (re-exported)
from path_planner import PathPlanner, is_on_road, snap_coordinate
from rider import IDLE, Rider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "initial_funds": 10000,
    "recruit_cost": 500,
    "max_riders": 10,
    "delivery_fee": 80,
    "operating_cost_per_tick": 1,
    "random_seed": None,
}

_INT_KEYS = ("initial_funds", "recruit_cost", "max_riders", "delivery_fee", "operating_cost_per_tick")


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load system parameters from a JSON file, falling back to defaults.

    The file may contain a top-level ``"parameters"`` object, or the parameters
    may be given at the top level. Unknown keys are ignored.

    Args:
        path: Path to the JSON configuration file, or None to use defaults.

    Returns:
        A dictionary of system parameters.
    """
    config = dict(DEFAULT_CONFIG)
    if not path:
        return config
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        logger.info("No configuration file at %s; using defaults", path)
        return config
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read configuration %s: %s", path, exc)
        return config

    if not isinstance(data, dict):
        logger.warning("Configuration %s is not a JSON object; using defaults", path)
        return config
    params = data.get("parameters", data)
    if not isinstance(params, dict):
        return config

    for key in _INT_KEYS:
        if key in params:
            try:
                config[key] = int(params[key])
            except (TypeError, ValueError):
                logger.warning("Invalid value for %s in %s; using default", key, path)
    if "random_seed" in params:
        config["random_seed"] = params["random_seed"]
    return config


def init_system(config_path: Optional[str] = None) -> "SystemManager":
    """Initialise global state and return the system manager.

    Resets the global store, loads configuration, sets the starting funds,
    creates the seeded random generator, and sets the running flag to True.

    Args:
        config_path: Optional path to a JSON configuration file.

    Returns:
        A ready-to-use SystemManager.
    """
    globalvar._init()
    config = load_config(config_path)
    set_value("config", config)
    set_value("funds", int(config["initial_funds"]))
    set_value("rng", random.Random(config.get("random_seed")))
    set_value("running", True)
    set_value("tick", 0)
    logger.info("System initialised with funds %s", config["initial_funds"])
    return SystemManager()


def recruit_rider() -> Optional[Rider]:
    """Recruit a new rider if the limit and funds allow.

    The recruitment cost is deducted from system funds. The new rider gets the
    next auto-incremented ID and is appended to the global rider list.

    Returns:
        The new Rider, or None when recruitment is not possible.
    """
    config = get_value("config", {})
    riders = get_value("riders", [])
    if len(riders) >= int(config.get("max_riders", 10)):
        logger.info("Recruitment skipped: rider limit reached")
        return None
    cost = int(config.get("recruit_cost", 0))
    funds = int(get_value("funds", 0))
    if funds < cost:
        logger.warning("Recruitment skipped: funds %s below cost %s", funds, cost)
        return None
    set_value("funds", funds - cost)
    rider_id = next_id("rider_id_counter")
    rider = Rider(rider_id, rng=get_value("rng"))
    riders.append(rider)
    logger.info("Recruited rider %s at (%s, %s)", rider.rider_id, rider.x, rider.y)
    return rider


class SystemManager:
    """Coordinates funds, riders, orders, and the simulation clock.

    Attributes:
        order_manager: Order creation and assignment helper.
        planner: Path planner used for route previews.
    """

    def __init__(self) -> None:
        """Create the manager using the current global state."""
        self.order_manager = OrderManager()
        self.planner = PathPlanner(get_value("rng"))

    @property
    def funds(self) -> int:
        """Current system fund balance (may be negative)."""
        return int(get_value("funds", 0))

    @property
    def riders(self) -> List[Rider]:
        """The live rider list."""
        return get_value("riders", [])

    @property
    def tick_count(self) -> int:
        """Current simulation tick."""
        return int(get_value("tick", 0))

    @property
    def config(self) -> Dict[str, Any]:
        """Loaded system parameters."""
        return get_value("config", {})

    def stop(self) -> None:
        """Clear the running flag so the main loop exits."""
        set_value("running", False)

    def should_recruit(self) -> bool:
        """Return True when riders are insufficient and funds allow recruitment.

        Recruitment is considered when the rider limit is not reached, funds
        cover the cost, and either no riders exist or every rider is busy.
        """
        cfg = self.config
        riders = self.riders
        if len(riders) >= int(cfg.get("max_riders", 10)):
            return False
        if self.funds < int(cfg.get("recruit_cost", 0)):
            return False
        if not riders:
            return True
        return all(rider.orders for rider in riders)

    def submit_order(self, coordinates: List[object]) -> Dict[str, Any]:
        """Create an order, recruit if needed, assign it, and preview its route.

        Args:
            coordinates: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Returns:
            Dictionary with keys ``order``, ``rider``, ``new_rider``,
            ``queued_ahead``, and ``route`` (the route dictionary).

        Raises:
            ValueError: If the coordinates are invalid.
            NoRiderAvailableError: If no rider can serve the order.
        """
        order = self.order_manager.create_order(coordinates)
        try:
            new_rider = False
            if self.should_recruit():
                new_rider = recruit_rider() is not None
            rider = self.order_manager.assign_order(order)
        except Exception:
            self.order_manager.discard_order(order)
            raise
        queued_ahead = len(rider.orders) - 1
        route = self.plan_route(rider, order)
        return {
            "order": order,
            "rider": rider,
            "new_rider": new_rider,
            "queued_ahead": queued_ahead,
            "route": route,
        }

    def plan_route(self, rider: Rider, order: Any) -> Dict[str, Any]:
        """Build the route from the rider's position through restaurant to customer.

        Args:
            rider: Rider assigned to the order.
            order: The order being routed.

        Returns:
            Dictionary with ``points``, ``pickup_distance``, ``delivery_distance``,
            and ``eta_ticks``. The ETA ignores orders queued ahead of this one.
        """
        to_restaurant = self.planner.find_path(rider.position(), order.res_pos) or []
        to_customer = self.planner.find_path(order.res_pos, order.cus_pos) or []
        speed = max(1, int(rider.speed))
        eta = math.ceil(len(to_restaurant) / speed) + math.ceil(len(to_customer) / speed)
        return {
            "points": [rider.position()] + to_restaurant + to_customer,
            "pickup_distance": len(to_restaurant),
            "delivery_distance": len(to_customer),
            "eta_ticks": eta,
        }

    def tick(self) -> int:
        """Advance the simulation by one tick.

        Increments the clock, charges operating costs for each rider, and moves
        every rider. Exceptions from a single rider are logged and do not stop
        the other riders.

        Returns:
            The new tick value.
        """
        set_value("tick", self.tick_count + 1)
        riders = list(self.riders)
        cost = int(self.config.get("operating_cost_per_tick", 0)) * len(riders)
        set_value("funds", self.funds - cost)
        for rider in riders:
            try:
                rider.move()
            except Exception:  # keep the simulation running after an unexpected error
                logger.exception("Rider %s failed during tick %s", rider.rider_id, self.tick_count)
        return self.tick_count

    def check_consistency(self) -> List[str]:
        """Detect and repair inconsistent system state.

        Repairs performed: removes completed orders from rider lists, resets
        riders that have a target but no orders, snaps off-street riders onto
        the nearest street, and restores integer funds.

        Returns:
            Human-readable descriptions of the issues found and repaired.
        """
        issues: List[str] = []
        riders = self.riders

        if not isinstance(get_value("funds"), int):
            issues.append("funds were not an integer; reset to integer value")
            set_value("funds", int(get_value("funds", 0) or 0))

        seen_ids = set()
        for rider in riders:
            if rider.rider_id in seen_ids:
                issues.append(f"duplicate rider id {rider.rider_id} detected")
            seen_ids.add(rider.rider_id)

            active = [o for o in rider.orders if o.status != "completed"]
            if len(active) != len(rider.orders):
                issues.append(f"rider {rider.rider_id} held completed orders; removed")
                rider.orders[:] = active

            if rider.state != IDLE and not rider.orders:
                issues.append(f"rider {rider.rider_id} was busy without orders; reset to idle")
                rider._become_idle()

            if not is_on_road(rider.x, rider.y):
                new_x = rider.x if rider.x % 100 == 0 else rider.x
                new_y = rider.y if rider.y % 100 == 0 else snap_coordinate(rider.y)
                if not is_on_road(new_x, new_y):
                    new_x = snap_coordinate(rider.x)
                issues.append(f"rider {rider.rider_id} was off-street; moved to ({new_x}, {new_y})")
                rider.x, rider.y = new_x, new_y
                rider.path = []
                rider.target = None
                rider.state = IDLE if not rider.orders else rider.state
        for issue in issues:
            logger.warning("Consistency: %s", issue)
        return issues

    def save_state(self, path: str) -> None:
        """Write parameters, funds, riders, and order history to a JSON file.

        The file is written to a temporary name and then moved into place, so a
        crash during the write does not corrupt the previous file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        data = {
            "parameters": self.config,
            "funds": self.funds,
            "tick": self.tick_count,
            "rider_id_counter": get_value("rider_id_counter", 0),
            "order_id_counter": get_value("order_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in get_value("orders", [])],
        }
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp_path, path)
        logger.info("State saved to %s", path)
