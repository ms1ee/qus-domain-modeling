"""System-level resource management and simulation control."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Sequence

import globalvar
from order import OrderManager
from order_model import Order
from rider import IDLE, Rider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "initial_funds": 1000,
    "recruit_cost": 300,
    "recruit_threshold": 300,
    "rider_speed": 10,
    "max_ticks_per_order": 5000,
}


class SystemManager:
    """Manages funds, riders, pending orders and the simulation clock.

    Recruitment rule: when funds are at least ``recruit_threshold`` and the
    number of pending orders exceeds the number of idle riders, a new rider
    is created at a cost of ``recruit_cost``.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """Create the manager.

        Args:
            config: System parameters (see DEFAULT_CONFIG).
        """
        self.config: Dict[str, Any] = dict(config)
        self.order_manager = OrderManager()

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    @property
    def funds(self) -> int:
        """Current system fund balance."""
        return int(globalvar.get_value("funds", 0))

    @property
    def riders(self) -> List[Rider]:
        """The live rider list."""
        return globalvar.get_value("riders")

    @property
    def time(self) -> int:
        """Current simulated tick."""
        return int(globalvar.get_value("time", 0))

    @property
    def running(self) -> bool:
        """Main loop running flag."""
        return bool(globalvar.get_value("running", False))

    @property
    def orders(self) -> List[Order]:
        """All orders created in this session."""
        return globalvar.get_value("orders")

    def pending_orders(self) -> List[Order]:
        """Return the live list of orders waiting for a rider."""
        return globalvar.get_value("pending_orders")

    def active_orders(self) -> List[Order]:
        """Return orders that have not yet been completed."""
        return [o for o in self.orders if o.status != "completed"]

    def stop(self) -> None:
        """Clear the running flag so the main loop exits."""
        globalvar.set_value("running", False)

    def get_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with ``rider_id``, or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def idle_rider_count(self) -> int:
        """Return the number of riders with state 0 and no orders."""
        return sum(1 for r in self.riders
                   if r.state == IDLE and not r.orders)

    # ------------------------------------------------------------------
    # Resource management
    # ------------------------------------------------------------------
    def recruit_rider(self) -> Optional[Rider]:
        """Create a new rider if funds cover the recruitment cost.

        Returns:
            The new Rider, or None if funds are insufficient.
        """
        cost = int(self.config["recruit_cost"])
        if self.funds < cost:
            logger.info("Recruitment skipped: funds %s < cost %s",
                        self.funds, cost)
            return None
        counter = int(globalvar.get_value("rider_id_counter", 0)) + 1
        globalvar.set_value("rider_id_counter", counter)
        globalvar.set_value("funds", self.funds - cost)
        rider = Rider(counter, speed=int(self.config["rider_speed"]))
        self.riders.append(rider)
        logger.info("Recruited rider %s (funds now %s)",
                    rider.rider_id, self.funds)
        return rider

    # ------------------------------------------------------------------
    # Order handling
    # ------------------------------------------------------------------
    def submit_order(self, res_pos: Sequence[int],
                     cus_pos: Sequence[int]) -> Order:
        """Create an order and try to dispatch it immediately.

        Args:
            res_pos: Restaurant coordinates ``(x, y)`` in range 0-800.
            cus_pos: Customer coordinates ``(x, y)`` in range 0-800.

        Returns:
            The created Order. Check ``order.rider_id`` to see whether it has
            been assigned; unassigned orders stay pending.
        """
        order = self.order_manager.create_order(res_pos, cus_pos)
        self.pending_orders().append(order)
        self.dispatch_pending()
        return order

    def dispatch_pending(self) -> List[Rider]:
        """Recruit riders when needed and assign pending orders.

        Returns:
            Riders recruited during this call.
        """
        recruited: List[Rider] = []
        threshold = int(self.config["recruit_threshold"])
        for order in list(self.pending_orders()):
            while (self.funds >= threshold
                   and len(self.pending_orders()) > self.idle_rider_count()):
                rider = self.recruit_rider()
                if rider is None:
                    break
                recruited.append(rider)
            if self.order_manager.assign_order(order) is not None:
                self.pending_orders().remove(order)
        return recruited

    # ------------------------------------------------------------------
    # Simulation loop
    # ------------------------------------------------------------------
    def tick(self) -> None:
        """Advance the simulation by one tick.

        Dispatches pending orders, moves every rider, then increments the
        clock. Exceptions from a single rider are logged and do not stop the
        simulation.
        """
        if not self.running:
            return
        self.dispatch_pending()
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # error recovery: keep other riders running
                logger.exception("Rider %s failed to move", rider.rider_id)
        globalvar.set_value("time", self.time + 1)

    def run_until_order_done(self, order: Order,
                             max_ticks: Optional[int] = None) -> bool:
        """Run ticks until ``order`` is completed.

        Args:
            order: Order to wait for.
            max_ticks: Tick limit; defaults to the configured value.

        Returns:
            True if the order was completed within the limit.
        """
        limit = int(max_ticks if max_ticks is not None
                    else self.config["max_ticks_per_order"])
        ticks = 0
        while order.status != "completed" and ticks < limit and self.running:
            self.tick()
            ticks += 1
        return order.status == "completed"

    def check_consistency(self) -> List[str]:
        """Return a list of detected state inconsistencies (empty if none)."""
        issues: List[str] = []
        seen: Dict[int, int] = {}
        for rider in self.riders:
            for order in rider.orders:
                if order.id in seen:
                    issues.append(f"order {order.id} held by two riders")
                seen[order.id] = rider.rider_id
                if order.status == "completed":
                    issues.append(f"completed order {order.id} still assigned")
        for order in self.pending_orders():
            if order.id in seen:
                issues.append(f"pending order {order.id} also assigned")
        return issues

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the system."""
        return {
            "time": self.time,
            "funds": self.funds,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "config": self.config,
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.orders],
            "pending_order_ids": [o.id for o in self.pending_orders()],
        }

    def save_state(self, path: str) -> bool:
        """Write the system snapshot to a JSON file.

        Args:
            path: Destination file path.

        Returns:
            True on success, False if the file could not be written.
        """
        try:
            directory = os.path.dirname(os.path.abspath(path))
            os.makedirs(directory, exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self.to_dict(), handle, indent=2)
            return True
        except (OSError, TypeError, ValueError) as exc:
            logger.error("Failed to save state to %s: %s", path, exc)
            return False


def load_config(path: str) -> Dict[str, Any]:
    """Load system parameters from a JSON configuration file.

    Unknown keys are ignored. Missing or invalid files yield an empty dict.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        A dictionary of recognised parameter overrides.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read config %s: %s", path, exc)
        return {}
    if not isinstance(data, dict):
        logger.warning("Config %s must contain a JSON object", path)
        return {}
    return {k: v for k, v in data.items() if k in DEFAULT_CONFIG}


def init_system(config_path: Optional[str] = None) -> SystemManager:
    """Initialise global state and return the system manager.

    Sets funds to 1000, an empty rider list, rider ID counter 0, running
    state True and time 0, then applies optional configuration overrides.

    Args:
        config_path: Optional JSON configuration file.

    Returns:
        A ready-to-use SystemManager.
    """
    globalvar._init()
    config = dict(DEFAULT_CONFIG)
    if config_path:
        config.update(load_config(config_path))
    globalvar.set_value("config", config)
    globalvar.set_value("funds", int(config["initial_funds"]))
    return SystemManager(config)
