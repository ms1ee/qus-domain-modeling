"""System state management: funds, riders, orders, ticks and persistence."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import globalvar
from globalvar import get_value, set_value
from order import OrderManager
from order_model import STATUS_COMPLETED, Order
from path_planner import default_planner
from rider import IDLE, PICKING_UP, Rider
from settings import CONFIG

logger = logging.getLogger("dispatch")


class SystemManager:
    """Core coordinator for funds, riders, orders and simulated time.

    Scalar state is stored in the global variable store (globalvar), so it
    is shared by all modules. Access goes through properties.
    """

    def __init__(self) -> None:
        self.order_manager = OrderManager()
        self._planner = default_planner()

    @property
    def funds(self) -> int:
        """System funds. Supports negative values."""
        value = get_value("funds")
        return value if isinstance(value, int) else 0

    @funds.setter
    def funds(self, value: int) -> None:
        set_value("funds", int(value))

    @property
    def rider_id_counter(self) -> int:
        """Last rider ID handed out."""
        value = get_value("rider_id_counter")
        return value if isinstance(value, int) else 0

    @rider_id_counter.setter
    def rider_id_counter(self, value: int) -> None:
        set_value("rider_id_counter", int(value))

    @property
    def running_state(self) -> bool:
        """True while the main loop should keep running."""
        return bool(get_value("running_state"))

    @running_state.setter
    def running_state(self, value: bool) -> None:
        set_value("running_state", bool(value))

    @property
    def simulated_time(self) -> int:
        """Current simulated tick count."""
        value = get_value("simulated_time")
        return value if isinstance(value, int) else 0

    @simulated_time.setter
    def simulated_time(self, value: int) -> None:
        set_value("simulated_time", int(value))

    @property
    def riders(self) -> List[Rider]:
        """The dynamic list of riders."""
        riders = get_value("riders")
        if riders is None:
            riders = []
            set_value("riders", riders)
        return riders

    def find_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with the given ID, or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def create_rider(self) -> Rider:
        """Create a new idle rider with an auto-incremented ID."""
        self.rider_id_counter = self.rider_id_counter + 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        logger.info("Rider %s recruited", rider.rider_id)
        return rider

    def remove_rider(self, rider_id: int) -> bool:
        """Remove an idle rider with no orders.

        Returns:
            True if the rider was removed, False if it was not found.

        Raises:
            ValueError: If the rider still has assigned orders.
        """
        rider = self.find_rider(rider_id)
        if rider is None:
            return False
        if rider.orders:
            raise ValueError(f"rider #{rider_id} still has active orders")
        self.riders.remove(rider)
        logger.info("Rider %s removed", rider_id)
        return True

    def recruit_riders(self) -> List[Rider]:
        """Recruit riders while funds are at or above the hiring threshold.

        Each recruitment consumes ``hire_cost`` funds.

        Returns:
            Riders that were created by this call.
        """
        hired: List[Rider] = []
        threshold = CONFIG["hire_threshold"]
        cost = CONFIG["hire_cost"]
        while self.funds >= threshold:
            self.funds = self.funds - cost
            hired.append(self.create_rider())
        return hired

    def submit_order(self, res_xy, cus_xy) -> Dict[str, Any]:
        """Create an order and try to assign it immediately.

        Recruitment is checked first, so a newly hired rider can take the order.

        Returns:
            Dict with keys ``order``, ``rider`` (or None), ``new_riders`` (list)
            and ``route`` (Route or None).
        """
        new_riders = self.recruit_riders()
        order = self.order_manager.create_order(res_xy, cus_xy, self.simulated_time)
        rider = self.order_manager.try_assign(order)
        route = None
        if rider is not None:
            route = self._planner.plan_route(
                (rider.x, rider.y),
                [order.res_pos.center, order.cus_pos.center],
                rider.speed,
            )
        return {"order": order, "rider": rider, "new_riders": new_riders, "route": route}

    def tick(self, count: int = 1) -> List[Order]:
        """Advance the simulation by ``count`` ticks.

        Each tick moves every rider, settles completed deliveries (paying the
        delivery fee), recruits riders if funds allow, and assigns pending orders.
        A failure in one rider is logged and recovered without stopping the others.

        Returns:
            Orders delivered during these ticks.
        """
        delivered: List[Order] = []
        for _ in range(count):
            self.simulated_time = self.simulated_time + 1
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception:  # noqa: BLE001 - keep the simulation running
                    logger.exception("Rider %s failed; recovering", rider.rider_id)
                    rider.recover()
            done = self.order_manager.collect_completed()
            for _order in done:
                self.funds = self.funds + CONFIG["delivery_fee"]
            delivered.extend(done)
            self.recruit_riders()
            self.order_manager.assign_pending()
        return delivered

    def verify_consistency(self) -> List[str]:
        """Check the state for inconsistencies.

        Returns:
            Human-readable problem descriptions. Empty if the state is consistent.
        """
        problems: List[str] = []
        seen_ids = set()
        limit = CONFIG["map_size"]
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                problems.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)
            if not (0 <= rider.x <= limit and 0 <= rider.y <= limit):
                problems.append(f"rider #{rider.rider_id} is off the map")
            if rider.state == IDLE and rider.orders:
                problems.append(f"rider #{rider.rider_id} is idle but has orders")
            if rider.state != IDLE and not rider.orders:
                problems.append(f"rider #{rider.rider_id} is busy without orders")
            for order in rider.orders:
                if order.status == STATUS_COMPLETED:
                    problems.append(f"completed order #{order.id} still on rider #{rider.rider_id}")
                if order.rider_id != rider.rider_id:
                    problems.append(f"order #{order.id} is not bound to rider #{rider.rider_id}")
        return problems

    def repair(self) -> List[str]:
        """Fix the problems that verify_consistency() can detect.

        Returns:
            Descriptions of the repair actions taken.
        """
        actions: List[str] = []
        for rider in self.riders:
            before = len(rider.orders)
            rider.orders = [o for o in rider.orders if o.status != STATUS_COMPLETED]
            if len(rider.orders) != before:
                actions.append(f"removed completed orders from rider #{rider.rider_id}")
            inconsistent = (rider.state == IDLE) != (not rider.orders)
            if inconsistent or rider.state not in (IDLE, PICKING_UP, 2):
                rider.recover()
                actions.append(f"re-planned rider #{rider.rider_id}")
        return actions

    def save_state(self, path: str) -> str:
        """Write the configuration, riders and order history to a JSON file.

        The file is written to a temporary name and then moved into place, so
        a failed write does not leave a corrupt file behind.

        Returns:
            The path that was written.
        """
        state = {
            "config": dict(CONFIG),
            "simulated_time": self.simulated_time,
            "funds": self.funds,
            "rider_id_counter": self.rider_id_counter,
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.order_manager.orders],
            "pending_order_ids": [o.id for o in self.order_manager.pending],
        }
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2)
        os.replace(tmp_path, path)
        logger.info("State saved to %s", path)
        return path


def init_system() -> SystemManager:
    """Initialise global variables and return a fresh SystemManager.

    Sets the rider list to empty, the rider ID counter to 0, the running state
    to True, simulated time to 0, and funds to the configured starting amount.

    Returns:
        The initialised SystemManager.
    """
    globalvar._init()
    set_value("riders", [])
    set_value("rider_id_counter", 0)
    set_value("running_state", True)
    set_value("simulated_time", 0)
    set_value("funds", CONFIG["initial_funds"])
    return SystemManager()
