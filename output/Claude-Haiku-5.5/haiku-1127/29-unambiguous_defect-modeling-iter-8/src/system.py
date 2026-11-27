"""System manager: funds, rider recruitment, order dispatch and ticks."""

import json
import logging
import math
import os
import time
from typing import Any, Dict, List, Optional

import globalvar
from config import Configuration
from grid_map import GridMap
from order import OrderManager
from order_model import Order
from path_planner import PathPlanner
from rider import Rider

logger = logging.getLogger("dispatch.system")


class DispatchError(RuntimeError):
    """Raised when a request cannot be fulfilled by the dispatch system."""


def init_system(config: Optional[Configuration] = None) -> "SystemManager":
    """Initialise global variables and create the system manager.

    Args:
        config: Configuration to use; loaded from file when None.

    Returns:
        The initialised SystemManager.
    """
    cfg = config if config is not None else Configuration.load()
    globalvar._init()
    globalvar.set_value("funds", int(cfg.initial_funds))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("is_running", True)
    globalvar.set_value("current_tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("recruitment_cost", int(cfg.recruitment_cost))
    globalvar.set_value("delivery_fee", int(cfg.delivery_fee))
    globalvar.set_value("default_rider_speed", int(cfg.default_rider_speed))
    globalvar.set_value("max_orders_per_rider", int(cfg.max_orders_per_rider))
    logger.info("System initialised with funds=%s", cfg.initial_funds)
    return SystemManager(cfg)


class SystemManager:
    """Core coordinator for funds, riders, orders and simulated time.

    Funds, riders, the rider ID counter, the running flag and the current
    tick are stored in the global variable store so every module shares them.
    """

    def __init__(self, config: Configuration) -> None:
        """Create the manager.

        Args:
            config: System configuration.
        """
        self.config = config
        self.grid = GridMap()
        self.planner = PathPlanner(self.grid)
        self.order_manager = OrderManager()
        self.recruitment_cost = int(config.recruitment_cost)

    # ------------------------------------------------------------------
    # Global-backed properties
    # ------------------------------------------------------------------
    @property
    def funds(self) -> int:
        """System fund balance (may be negative)."""
        return int(globalvar.get_value("funds") or 0)

    @funds.setter
    def funds(self, value: int) -> None:
        globalvar.set_value("funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """List of all riders."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def rider_id_counter(self) -> int:
        """Last rider ID handed out."""
        return int(globalvar.get_value("rider_id_counter") or 0)

    @rider_id_counter.setter
    def rider_id_counter(self, value: int) -> None:
        globalvar.set_value("rider_id_counter", int(value))

    @property
    def is_running(self) -> bool:
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("is_running"))

    @is_running.setter
    def is_running(self, value: bool) -> None:
        globalvar.set_value("is_running", bool(value))

    @property
    def current_tick(self) -> int:
        """Current simulated time."""
        return int(globalvar.get_value("current_tick") or 0)

    @current_tick.setter
    def current_tick(self, value: int) -> None:
        globalvar.set_value("current_tick", int(value))

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------
    def get_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with the given identifier.

        Args:
            rider_id: Rider identifier.

        Returns:
            The Rider, or None if not found.
        """
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def find_order(self, order_id: int) -> Optional[Order]:
        """Return the order with the given identifier.

        Args:
            order_id: Order identifier.

        Returns:
            The Order, or None if not found.
        """
        for order in self.order_manager.orders:
            if order.id == order_id:
                return order
        return None

    # ------------------------------------------------------------------
    # Recruitment and dispatch
    # ------------------------------------------------------------------
    def recruit_rider(self) -> Optional[Rider]:
        """Recruit a new rider if funds and the rider limit allow it.

        Returns:
            The new Rider, or None if recruitment was not possible.
        """
        if len(self.riders) >= self.config.max_riders:
            return None
        if self.funds < self.recruitment_cost:
            return None
        self.rider_id_counter = self.rider_id_counter + 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        self.funds = self.funds - self.recruitment_cost
        logger.info("Recruited rider #%s", rider.rider_id)
        return rider

    def submit_order(self, restaurant_pos, customer_pos) -> Dict[str, Any]:
        """Create an order and assign it to a rider.

        A new rider is recruited when no rider is idle and recruitment is
        possible. The best rider is then chosen by distance and load.

        Args:
            restaurant_pos: Restaurant raw position (x, y).
            customer_pos: Customer raw position (x, y).

        Returns:
            Dictionary describing the accepted order and its route.

        Raises:
            DispatchError: If no rider can take the order.
        """
        order = self.order_manager.create_order(restaurant_pos, customer_pos)
        new_rider = False
        if not any(not r.orders for r in self.riders):
            if self.recruit_rider() is not None:
                new_rider = True
        rider = self.order_manager.assign(order)
        if rider is None:
            self.order_manager.discard(order)
            raise DispatchError(
                "no rider is available and recruitment is not possible "
                "(insufficient funds or rider limit reached)."
            )
        route = self.planner.plan_route(
            [(rider.x, rider.y), order.res_pos, order.cus_pos]
        )
        order.distance = float(self.planner.path_length(route))
        eta = math.ceil(order.distance / rider.speed) if rider.speed > 0 else 0
        logger.info("Order #%s assigned to rider #%s", order.id, rider.rider_id)
        return {
            "order": order,
            "rider": rider,
            "order_id": order.id,
            "restaurant": order.res_pos,
            "customer": order.cus_pos,
            "new_rider": new_rider,
            "speed": rider.speed,
            "route": route,
            "distance": order.distance,
            "estimated_ticks": eta,
        }

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def tick(self) -> None:
        """Advance the simulation by one time unit.

        Every rider moves once, upkeep is charged for busy riders, and the
        state is checked for consistency. Failures in one rider do not stop
        the others.
        """
        self.current_tick = self.current_tick + 1
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # noqa: BLE001 - recover per rider
                logger.exception("Rider #%s failed; resetting its route.",
                                 rider.rider_id)
                rider.reset_route()
        busy = sum(1 for r in self.riders if r.orders)
        self.funds = self.funds - busy * self.config.rider_upkeep
        for issue in self.check_consistency():
            logger.warning(issue)

    def check_consistency(self) -> List[str]:
        """Verify and repair consistency between riders and orders.

        Returns:
            List of human-readable descriptions of issues found and fixed.
        """
        issues: List[str] = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)
            for order in list(rider.orders):
                if order.status in ("completed", "rejected"):
                    rider.orders.remove(order)
                    issues.append(
                        f"removed finished order #{order.id} "
                        f"from rider #{rider.rider_id}"
                    )
                elif order.rider_id != rider.rider_id:
                    issues.append(
                        f"order #{order.id} rider mismatch; "
                        f"set to rider #{rider.rider_id}"
                    )
                    order.rider_id = rider.rider_id
            before = rider.state
            rider.refresh_state()
            if before != rider.state:
                issues.append(
                    f"rider #{rider.rider_id} state corrected {before}->{rider.state}"
                )
        for order in self.order_manager.active_orders():
            if order.rider_id is not None and order.rider_id not in seen_ids:
                issues.append(f"order #{order.id} references missing rider")
        return issues

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save_state(self, path: Optional[str] = None) -> str:
        """Save configuration, riders and order history to a JSON file.

        The file is written to a temporary name first and then renamed, so
        an interrupted save does not corrupt the previous state.

        Args:
            path: Destination file; defaults to the configured state path.

        Returns:
            The path that was written.

        Raises:
            OSError: If the file cannot be written.
        """
        target = path or self.config.state_file_path
        data = {
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config": self.config.to_dict(),
            "funds": self.funds,
            "current_tick": self.current_tick,
            "rider_id_counter": self.rider_id_counter,
            "riders": [
                {
                    "rider_id": r.rider_id,
                    "x": r.x,
                    "y": r.y,
                    "speed": r.speed,
                    "state": r.state,
                    "special_case": r.special_case,
                    "order_ids": [o.id for o in r.orders],
                    "distance_traveled": r.distance_traveled,
                    "log": r.log,
                }
                for r in self.riders
            ],
            "orders": [o.to_dict() for o in self.order_manager.orders],
        }
        tmp_path = target + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp_path, target)
        logger.info("State saved to %s", target)
        return target
