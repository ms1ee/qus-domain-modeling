"""Core system manager: funds, rider recruitment, order flow and ticks.

``init_system`` sets up the global variables, the initial funds and the
first rider. The ``SystemManager`` coordinates orders, riders and the
simulated clock.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Sequence

import config
import globalvar
from grid import Point
from order import OrderManager
from order_model import (
    STATUS_ASSIGNED,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_PICKED_UP,
    Order,
)
from path_planner import PathPlanner
from rider import DEPOT, STATE_DELIVERING, STATE_IDLE, STATE_PICKING_UP, Rider

logger = logging.getLogger(__name__)

_manager: Optional["SystemManager"] = None


class SystemManager:
    """Manages funds, riders, orders and the simulated clock."""

    def __init__(self) -> None:
        """Create the manager with its order manager and path planner."""
        self.order_manager = OrderManager()
        self.planner = PathPlanner()

    # ------------------------------------------------------------------
    # Funds, riders and state accessors
    # ------------------------------------------------------------------
    @property
    def funds(self) -> int:
        """Current system fund balance."""
        return int(globalvar.get_value("funds", 0))

    @property
    def tick_count(self) -> int:
        """Current simulated tick."""
        return int(globalvar.get_value("tick", 0))

    @property
    def riders(self) -> List[Rider]:
        """The dynamic rider list."""
        return globalvar.get_value("riders", [])

    def all_orders(self) -> List[Order]:
        """Return every order created in this session."""
        return list(globalvar.get_value("orders", []) or [])

    def active_orders(self) -> List[Order]:
        """Return orders that are not yet completed."""
        return [o for o in self.all_orders() if o.status != STATUS_COMPLETED]

    def add_funds(self, amount: int) -> None:
        """Add ``amount`` (may be negative) to the fund balance."""
        globalvar.set_value("funds", self.funds + int(amount))

    def create_rider(self) -> Rider:
        """Create a new rider at the depot and add it to the rider list."""
        rider_id = globalvar.next_counter("rider_id_counter")
        rider = Rider(rider_id, DEPOT[0], DEPOT[1])
        self.riders.append(rider)
        return rider

    def check_recruitment(self) -> Optional[Rider]:
        """Recruit a rider if funds reach the recruitment threshold.

        Recruiting costs ``rider_cost`` from the fund balance.

        Returns:
            The new Rider, or None if no recruitment happened.
        """
        if self.funds >= int(config.CONFIG["recruit_threshold"]):
            self.add_funds(-int(config.CONFIG["rider_cost"]))
            rider = self.create_rider()
            logger.info("Recruited rider %d", rider.rider_id)
            return rider
        return None

    # ------------------------------------------------------------------
    # Order flow
    # ------------------------------------------------------------------
    def build_route(self, order: Order, rider: Rider) -> List[Point]:
        """Build the full route rider -> restaurant -> customer.

        Args:
            order: The order being planned.
            rider: The rider that will execute it.

        Returns:
            List of points starting at the rider's position.
        """
        start = rider.position
        route: List[Point] = [start]
        route.extend(self.planner.plan(start, order.restaurant_center))
        route.extend(
            self.planner.plan(order.restaurant_center, order.customer_center)
        )
        return route

    def process_order(
        self, res_pos: Sequence[int], cus_pos: Sequence[int]
    ) -> Dict[str, Any]:
        """Handle a ``start`` request: create, fund, recruit and assign.

        Args:
            res_pos: Restaurant ``(x, y)`` input coordinate.
            cus_pos: Customer ``(x, y)`` input coordinate.

        Returns:
            Dictionary with keys ``order``, ``rider`` (assigned or None),
            ``new_rider`` (recruited Rider or None), ``route``, ``speed``,
            ``route_length``, ``eta_ticks`` and ``queue_ahead``.

        Raises:
            ValueError: If a coordinate is invalid.
        """
        order = self.order_manager.create_order(res_pos, cus_pos)
        self.add_funds(int(config.CONFIG["order_revenue"]))
        new_rider = self.check_recruitment()
        rider = self.order_manager.try_assign(order)
        route: List[Point] = []
        length = 0
        eta: Optional[int] = None
        speed: Optional[int] = None
        queue_ahead = 0
        if rider is not None:
            route = self.build_route(order, rider)
            length = PathPlanner.path_length(route)
            speed = rider.speed
            eta = math.ceil(length / speed)
            queue_ahead = len(rider.orders) - 1
        return {
            "order": order,
            "rider": rider,
            "new_rider": new_rider,
            "route": route,
            "speed": speed,
            "route_length": length,
            "eta_ticks": eta,
            "queue_ahead": queue_ahead,
        }

    def tick(self) -> List[Order]:
        """Advance the simulation by one unit of time.

        Every rider moves once, completed deliveries are settled, pending
        orders are retried and recruitment is re-checked.

        Returns:
            Orders completed during this tick.
        """
        now = self.tick_count + 1
        globalvar.set_value("tick", now)
        completed: List[Order] = []
        for rider in list(self.riders):
            try:
                done = rider.move()
            except Exception:  # pylint: disable=broad-except
                logger.exception("Rider %d failed to move", rider.rider_id)
                continue
            if done is not None:
                self._on_order_completed(done)
                completed.append(done)
        self.order_manager.assign_pending()
        self.check_recruitment()
        return completed

    def _on_order_completed(self, order: Order) -> None:
        """Apply late-delivery penalties and log the completion."""
        late = int(config.CONFIG["late_threshold_ticks"])
        if order.time_taken is not None and order.time_taken > late:
            self.add_funds(-int(config.CONFIG["late_penalty"]))
            logger.info("Order %d was late (%d ticks)", order.id,
                        order.time_taken)

    # ------------------------------------------------------------------
    # Consistency checks and recovery
    # ------------------------------------------------------------------
    def verify_state(self) -> List[str]:
        """Check internal consistency and return a list of problems."""
        problems: List[str] = []
        rider_ids = {rider.rider_id for rider in self.riders}
        if len(rider_ids) != len(self.riders):
            problems.append("duplicate rider IDs detected")
        for rider in self.riders:
            if rider.state == STATE_IDLE and rider.orders:
                problems.append(
                    f"rider {rider.rider_id} is idle but holds orders"
                )
            if rider.state != STATE_IDLE and not rider.orders:
                problems.append(
                    f"rider {rider.rider_id} is busy without orders"
                )
            for order in rider.orders:
                if order.status == STATUS_COMPLETED:
                    problems.append(
                        f"rider {rider.rider_id} holds completed order "
                        f"{order.id}"
                    )
        for order in self.all_orders():
            if order.status in (STATUS_ASSIGNED, STATUS_PICKED_UP):
                if order.rider_id not in rider_ids:
                    problems.append(
                        f"order {order.id} references missing rider "
                        f"{order.rider_id}"
                    )
        return problems

    def repair_state(self) -> List[str]:
        """Repair inconsistencies found by ``verify_state``.

        Returns:
            Human readable descriptions of the fixes applied.
        """
        fixes: List[str] = []
        rider_ids = {rider.rider_id: rider for rider in self.riders}
        for rider in self.riders:
            active = [o for o in rider.orders if o.status != STATUS_COMPLETED]
            if len(active) != len(rider.orders):
                rider.orders = active
                fixes.append(f"removed completed orders from rider "
                             f"{rider.rider_id}")
            if rider.orders:
                expected = (
                    STATE_DELIVERING
                    if rider.orders[0].status == STATUS_PICKED_UP
                    else STATE_PICKING_UP
                )
                if rider.state != expected:
                    rider.state = expected
                    rider.route = []
                    fixes.append(f"reset state of rider {rider.rider_id}")
            elif rider.state != STATE_IDLE:
                rider.state = STATE_IDLE
                rider.route = []
                fixes.append(f"set rider {rider.rider_id} to idle")
        for order in self.all_orders():
            if order.status not in (STATUS_ASSIGNED, STATUS_PICKED_UP):
                continue
            holder = rider_ids.get(order.rider_id)
            if holder is None or order not in holder.orders:
                order.status = STATUS_PENDING
                order.rider_id = None
                if order not in self.order_manager.pending:
                    self.order_manager.pending.append(order)
                fixes.append(f"re-queued order {order.id}")
        self.order_manager.pending = [
            o for o in self.order_manager.pending
            if o.status == STATUS_PENDING
        ]
        self.order_manager.assign_pending()
        return fixes

    def export_state(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the whole system."""
        return {
            "tick": self.tick_count,
            "funds": self.funds,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "order_id_counter": globalvar.get_value("order_id_counter", 0),
            "config": dict(config.CONFIG),
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.all_orders()],
        }


def init_system() -> None:
    """Initialise global variables and the system manager.

    Sets the initial funds, the clock and the empty rider and order lists,
    then performs the automatic recruitment check (which spawns the first
    rider when the initial funds reach the threshold).
    """
    global _manager
    globalvar._init()  # pylint: disable=protected-access
    globalvar.set_value("funds", int(config.CONFIG["initial_funds"]))
    globalvar.set_value("tick", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("riders", [])
    globalvar.set_value("orders", [])
    _manager = SystemManager()
    globalvar.set_value("manager", _manager)
    _manager.check_recruitment()
    logger.info("System initialised with funds %d", _manager.funds)


def get_manager() -> SystemManager:
    """Return the active SystemManager, initialising the system if needed."""
    if _manager is None:
        init_system()
    assert _manager is not None
    return _manager
