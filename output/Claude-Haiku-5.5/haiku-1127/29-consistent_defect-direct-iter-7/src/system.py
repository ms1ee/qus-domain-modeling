"""System management: funds, rider recruitment, dispatch and persistence."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import globalvar
from order import OrderManager
from order_model import Order
from rider import IDLE, Rider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "initial_funds": 1000,
    "recruit_threshold": 300,
    "recruit_cost": 500,
    "spawn_position": [400, 400],
    "rider_speed": 20,
    "log_file": "dispatch.log",
}


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load system parameters from a JSON configuration file.

    Missing or invalid files fall back to ``DEFAULT_CONFIG``.

    Args:
        path: Path to the JSON configuration file, or None.

    Returns:
        Merged configuration dictionary.
    """
    config = dict(DEFAULT_CONFIG)
    config["spawn_position"] = list(DEFAULT_CONFIG["spawn_position"])
    if not path or not os.path.exists(path):
        return config
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("could not read config %s: %s", path, exc)
        return config
    if isinstance(data, dict):
        for key in DEFAULT_CONFIG:
            if key in data:
                config[key] = data[key]
    return config


def init_system(config_path: Optional[str] = None) -> None:
    """Initialise global variables and system parameters.

    Sets the system funds, empty rider list, rider ID counter (0), running
    state (True), order list and simulated clock (0).

    Args:
        config_path: Optional JSON configuration file path.
    """
    globalvar._init()
    config = load_config(config_path)
    globalvar.set_value("config", config)
    globalvar.set_value("funds", int(config["initial_funds"]))
    logger.info("system initialised with funds=%s", config["initial_funds"])


class SystemManager:
    """Core manager for funds, riders, dispatch, ticks and state checks."""

    def __init__(self) -> None:
        """Create the manager. Global state must already be initialised."""
        self.order_manager = OrderManager()

    # ----- global state accessors -------------------------------------
    @property
    def config(self) -> Dict[str, Any]:
        """Return the active configuration dictionary."""
        return globalvar.get_value("config") or DEFAULT_CONFIG

    @property
    def funds(self) -> int:
        """Return the system fund balance (may be negative)."""
        return int(globalvar.get_value("funds", 0) or 0)

    @funds.setter
    def funds(self, value: int) -> None:
        """Set the system fund balance."""
        globalvar.set_value("funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """Return the live rider list."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def current_tick(self) -> int:
        """Return the current simulated time."""
        return int(globalvar.get_value("tick", 0) or 0)

    def is_running(self) -> bool:
        """Return True while the main loop should keep running."""
        return bool(globalvar.get_value("running", False))

    def stop(self) -> None:
        """Request the main loop to exit."""
        globalvar.set_value("running", False)

    def rider_by_id(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with ``rider_id``, or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def idle_rider_count(self) -> int:
        """Return the number of riders without active orders."""
        return sum(1 for rider in self.riders if not rider.active_orders())

    # ----- recruitment -------------------------------------------------
    def should_recruit(self, pending_count: int) -> bool:
        """Return True when a new rider should be recruited.

        Args:
            pending_count: Number of pending orders.

        Returns:
            True if funds >= threshold and pending orders exceed idle riders.
        """
        threshold = int(self.config["recruit_threshold"])
        return self.funds >= threshold and pending_count > self.idle_rider_count()

    def recruit_rider(self) -> Optional[Rider]:
        """Create a new rider and deduct the recruitment cost.

        Returns:
            The new Rider, or None if funds are below the threshold.
        """
        cfg = self.config
        if self.funds < int(cfg["recruit_threshold"]):
            return None
        self.funds = self.funds - int(cfg["recruit_cost"])
        counter = int(globalvar.get_value("rider_id_counter", 0) or 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        spawn_x, spawn_y = cfg["spawn_position"]
        rider = Rider(counter, int(spawn_x), int(spawn_y), int(cfg["rider_speed"]))
        self.riders.append(rider)
        logger.info("recruited rider %s; funds now %s", counter, self.funds)
        return rider

    # ----- dispatch ----------------------------------------------------
    def dispatch_order(self, order: Order) -> Tuple[Optional[Rider], bool]:
        """Recruit if needed and assign ``order`` to a rider.

        Args:
            order: Pending order to dispatch.

        Returns:
            Tuple of (assigned rider or None, whether a new rider was added).
        """
        pending = len(self.order_manager.pending_orders())
        recruited = False
        if self.should_recruit(pending) and self.recruit_rider() is not None:
            recruited = True
        rider = self.order_manager.assign_order(order)
        return rider, recruited

    def dispatch_pending(self) -> int:
        """Try to dispatch every pending order.

        Returns:
            Number of orders assigned during this call.
        """
        assigned = 0
        for order in list(self.order_manager.pending_orders()):
            rider, _ = self.dispatch_order(order)
            if rider is not None:
                assigned += 1
        return assigned

    # ----- simulation clock -------------------------------------------
    def tick(self) -> None:
        """Advance the simulation by one unit of time."""
        globalvar.set_value("tick", self.current_tick + 1)
        try:
            self.dispatch_pending()
        except Exception:  # pragma: no cover - defensive recovery
            logger.exception("dispatch_pending failed during tick")
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive recovery
                logger.exception("rider %s failed to move", rider.rider_id)

    def run_ticks(self, count: int) -> int:
        """Advance the simulation ``count`` ticks.

        Args:
            count: Number of ticks to run.

        Returns:
            Number of orders completed during these ticks.
        """
        before = len(self.order_manager.completed_orders())
        for _ in range(count):
            self.tick()
        return len(self.order_manager.completed_orders()) - before

    # ----- consistency -------------------------------------------------
    def check_consistency(self) -> List[str]:
        """Check and repair system state consistency.

        Repairs performed:
            * Riders that are busy without active orders are reset to idle.
            * Orders marked as assigned but held by no rider return to pending.

        Returns:
            Human-readable description of each issue found and repaired.
        """
        issues: List[str] = []
        riders_by_id = {rider.rider_id: rider for rider in self.riders}
        for rider in self.riders:
            if rider.state != IDLE and not rider.active_orders():
                issues.append(
                    f"rider #{rider.rider_id} was {rider.state_name} with no orders; reset to idle"
                )
                rider.state = IDLE
                rider.target = None
                rider.route = []
        for order in globalvar.get_value("orders") or []:
            if order.status in ("assigned", "picking_up", "delivering"):
                holder = riders_by_id.get(order.rider_id)
                if holder is None or order not in holder.orders:
                    issues.append(
                        f"order #{order.id} was {order.status} but no rider holds it; returned to pending"
                    )
                    order.status = "pending"
                    order.rider_id = None
        if self.funds < 0:
            issues.append(f"system funds are negative ({self.funds})")
        return issues

    # ----- persistence -------------------------------------------------
    def save_state(self, path: str) -> None:
        """Save riders, orders, funds and clock to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            ValueError: If the file cannot be written.
        """
        data = {
            "funds": self.funds,
            "tick": self.current_tick,
            "rider_id_counter": int(globalvar.get_value("rider_id_counter", 0) or 0),
            "config": self.config,
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in globalvar.get_value("orders") or []],
        }
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
        except OSError as exc:
            raise ValueError(f"could not save state to '{path}': {exc}") from exc
        logger.info("state saved to %s", path)

    def load_state(self, path: str) -> None:
        """Restore riders, orders, funds and clock from a JSON file.

        Args:
            path: Source file path.

        Raises:
            ValueError: If the file is missing or malformed.
        """
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            orders = [Order.from_dict(item) for item in data.get("orders", [])]
            by_id = {order.id: order for order in orders}
            riders = [Rider.from_dict(item, by_id) for item in data.get("riders", [])]
        except OSError as exc:
            raise ValueError(f"could not read state file '{path}': {exc}") from exc
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"state file '{path}' is malformed: {exc}") from exc
        globalvar.set_value("orders", orders)
        globalvar.set_value("riders", riders)
        globalvar.set_value("funds", int(data.get("funds", self.funds)))
        globalvar.set_value("tick", int(data.get("tick", 0)))
        globalvar.set_value("rider_id_counter", int(data.get("rider_id_counter", len(riders))))
        self.check_consistency()
        logger.info("state loaded from %s", path)
