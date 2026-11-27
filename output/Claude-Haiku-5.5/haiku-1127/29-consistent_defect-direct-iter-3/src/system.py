"""System-level resource management and simulation control."""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from config import DEFAULTS, MAX_TICKS_PER_ORDER
from order import OrderManager
from order_model import Order
from rider import IDLE, PICKING_UP, Rider

logger = logging.getLogger("dispatch.system")


def init_system(params: Optional[Dict[str, Any]] = None) -> None:
    """Initialise the global system state.

    Sets funds to the initial amount, an empty rider list, the rider ID
    counter to 0, the running flag to True, the simulated clock to 0 and an
    empty order list.

    Args:
        params: Optional overrides for ``DEFAULTS`` (e.g. loaded from a
            configuration file).
    """
    globalvar._init()
    cfg = dict(DEFAULTS)
    if params:
        cfg.update(params)
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", int(cfg["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    logger.info("System initialised with funds=%s", cfg["initial_funds"])


class SystemManager:
    """Coordinates funds, riders, orders and the simulation clock."""

    def __init__(self, params: Optional[Dict[str, Any]] = None) -> None:
        """Initialise the system state and order manager.

        Args:
            params: Optional configuration overrides.
        """
        init_system(params)
        self.order_manager = OrderManager()

    # ------------------------------------------------------------------ funds
    def _cfg(self, key: str) -> int:
        """Return a configured integer parameter."""
        return int(globalvar.get_value("config")[key])

    def get_funds(self) -> int:
        """Return the current system fund balance."""
        return int(globalvar.get_value("funds"))

    def adjust_funds(self, delta: int) -> int:
        """Add ``delta`` (possibly negative) to the fund balance.

        Args:
            delta: Amount to add.

        Returns:
            The new balance.
        """
        new_value = self.get_funds() + int(delta)
        globalvar.set_value("funds", new_value)
        return new_value

    # ----------------------------------------------------------------- riders
    @staticmethod
    def riders() -> List[Rider]:
        """Return the live rider list."""
        return globalvar.get_value("riders")

    def next_rider_id(self) -> int:
        """Return a new unique rider ID and advance the counter."""
        counter = int(globalvar.get_value("rider_id_counter")) + 1
        globalvar.set_value("rider_id_counter", counter)
        return counter

    def create_rider(self) -> Rider:
        """Recruit a new rider, deducting the recruitment cost.

        Returns:
            The newly created rider.
        """
        rider = Rider(self.next_rider_id())
        self.riders().append(rider)
        self.adjust_funds(-self._cfg("recruit_cost"))
        logger.info("Recruited rider %s", rider.rider_id)
        return rider

    def idle_rider_count(self) -> int:
        """Return the number of riders with no active orders."""
        return sum(1 for rider in self.riders() if rider.is_idle())

    def pending_order_count(self) -> int:
        """Return the number of orders waiting for a rider."""
        return len(self.order_manager.pending_orders())

    def maybe_recruit(self) -> List[Rider]:
        """Recruit riders while pending orders exceed idle riders.

        Recruitment requires funds of at least ``recruit_min_funds``. Each
        recruit costs ``recruit_cost``.

        Returns:
            List of riders created during this call (possibly empty).
        """
        created: List[Rider] = []
        min_funds = self._cfg("recruit_min_funds")
        while (self.pending_order_count() > self.idle_rider_count()
               and self.get_funds() >= min_funds):
            created.append(self.create_rider())
        return created

    # ----------------------------------------------------------------- orders
    def submit_order(self, res_x: int, res_y: int, cus_x: int,
                     cus_y: int) -> Tuple[Order, Optional[Rider], List[Rider]]:
        """Create an order, recruit riders if needed, and assign the order.

        Args:
            res_x: Restaurant x coordinate.
            res_y: Restaurant y coordinate.
            cus_x: Customer x coordinate.
            cus_y: Customer y coordinate.

        Returns:
            Tuple ``(order, assigned_rider_or_None, recruited_riders)``.
        """
        order = self.order_manager.create_order(res_x, res_y, cus_x, cus_y)
        recruited = self.maybe_recruit()
        rider = self.order_manager.assign_order(order)
        return order, rider, recruited

    def all_orders(self) -> List[Order]:
        """Return all orders (completed and active)."""
        return self.order_manager.list_orders()

    # ------------------------------------------------------------- simulation
    @staticmethod
    def current_time() -> int:
        """Return the simulated clock value (ticks)."""
        return int(globalvar.get_value("time", 0))

    def tick(self) -> None:
        """Advance the simulation by one tick and move every rider."""
        globalvar.set_value("time", self.current_time() + 1)
        for rider in list(self.riders()):
            rider.move()

    def run_until_complete(self, order: Order,
                           max_ticks: Optional[int] = None) -> int:
        """Run ticks until the given order is completed.

        Args:
            order: Order to wait for. It must already be assigned.
            max_ticks: Safety limit on ticks.

        Returns:
            Number of ticks elapsed.

        Raises:
            ValueError: If the order has not been assigned to a rider.
            RuntimeError: If the order does not complete within the limit.
        """
        if order.rider_id is None:
            raise ValueError(f"order {order.id} is not assigned to a rider")
        limit = max_ticks if max_ticks is not None else self._cfg("max_ticks_per_order")
        if limit <= 0:
            limit = MAX_TICKS_PER_ORDER
        elapsed = 0
        while order.status != "completed":
            if elapsed >= limit:
                raise RuntimeError(f"order {order.id} not completed after {limit} ticks")
            self.tick()
            elapsed += 1
        return elapsed

    def stop(self) -> None:
        """Clear the running flag so the main loop exits."""
        globalvar.set_value("running", False)

    def check_consistency(self) -> List[str]:
        """Verify and automatically repair rider state consistency.

        Riders with active orders are forced into a non-idle state, and riders
        without active orders are forced to idle.

        Returns:
            Human-readable descriptions of repairs performed or problems found.
        """
        fixes: List[str] = []
        riders = self.riders()
        ids = [rider.rider_id for rider in riders]
        if len(ids) != len(set(ids)):
            fixes.append("duplicate rider IDs detected (cannot auto-fix)")
        for rider in riders:
            has_active = bool(rider.active_orders())
            if has_active and rider.state == IDLE:
                rider.state = PICKING_UP
                fixes.append(f"rider #{rider.rider_id}: idle with active orders -> picking up")
            elif not has_active and rider.state != IDLE:
                rider.state = IDLE
                rider.special_case = False
                fixes.append(f"rider #{rider.rider_id}: no active orders -> idle")
        known = set(ids)
        for order in self.all_orders():
            if (order.status != "completed" and order.rider_id is not None
                    and order.rider_id not in known):
                fixes.append(f"order #{order.id}: rider #{order.rider_id} missing (cannot auto-fix)")
        return fixes

    # ------------------------------------------------------------ persistence
    def save_state(self, path: str) -> str:
        """Write funds, riders, orders and configuration to a JSON file.

        Args:
            path: Destination file path.

        Returns:
            The path written.

        Raises:
            OSError: If the file cannot be written.
        """
        data = {
            "config": globalvar.get_value("config"),
            "funds": self.get_funds(),
            "rider_id_counter": globalvar.get_value("rider_id_counter"),
            "time": self.current_time(),
            "riders": [
                {
                    "rider_id": r.rider_id,
                    "x": r.x,
                    "y": r.y,
                    "speed": r.speed,
                    "state": r.state,
                    "special_case": r.special_case,
                    "order_ids": [o.id for o in r.orders],
                    "log": r.log,
                }
                for r in self.riders()
            ],
            "orders": [o.to_dict() for o in self.all_orders()],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("State saved to %s", path)
        return path
