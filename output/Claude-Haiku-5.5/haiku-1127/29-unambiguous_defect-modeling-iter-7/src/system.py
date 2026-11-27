"""Core system manager: funds, rider recruitment, order submission and clock."""

import logging
from typing import Dict, List, Optional

import globalvar
from config import DEFAULT_PARAMETERS
from grid import Grid
from order import OrderManager
from order_model import Order
from path_planner import PathPlanner, Route
from rider import STATE_IDLE, Rider

LOGGER = logging.getLogger(__name__)


class SystemManager:
    """Manages funds, riders, orders and the simulation clock.

    Attributes:
        funds: System funds (may go negative).
        rider_id_counter: Last rider ID issued.
        running_state: True while the main loop should keep running.
        current_tick: Simulated time.
        rider_recruitment_cost: Cost deducted for each new rider.
        max_riders: Upper bound on rider count.
        rider_speed: Speed given to newly recruited riders.
        grid: Map description.
        planner: Path planner used for route previews.
        order_manager: Order creation and assignment component.
    """

    def __init__(self, parameters: Optional[Dict] = None) -> None:
        """Create the system with the supplied or default parameters.

        Args:
            parameters: Optional overrides for DEFAULT_PARAMETERS.
        """
        params = dict(DEFAULT_PARAMETERS)
        params.update(parameters or {})
        self.funds = int(params["initial_funds"])
        self.rider_id_counter = 0
        self.running_state = True
        self.current_tick = 0
        self.rider_recruitment_cost = int(params["rider_recruitment_cost"])
        self.max_riders = int(params["max_riders"])
        self.rider_speed = int(params["rider_speed"])
        self.grid = Grid()
        self.planner = PathPlanner(self.grid)
        self.order_manager = OrderManager()
        globalvar.set_value("riders", [])
        globalvar.set_value("current_tick", 0)

    @property
    def riders(self) -> List[Rider]:
        """Return the shared rider list.

        Returns:
            List[Rider]: Riders currently managed by the system.
        """
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    def has_idle_rider(self) -> bool:
        """Return True if at least one rider has no assigned work.

        Returns:
            bool: Idle availability flag.
        """
        return any(rider.is_idle for rider in self.riders)

    def can_recruit(self) -> bool:
        """Return True when funds allow and the rider cap is not reached.

        Returns:
            bool: Recruitment feasibility.
        """
        return len(self.riders) < self.max_riders and self.funds >= self.rider_recruitment_cost

    def recruit_rider(self) -> Optional[Rider]:
        """Create a new rider and charge the recruitment cost.

        Returns:
            Rider: The new rider, or None if recruitment is not possible.
        """
        if not self.can_recruit():
            return None
        self.rider_id_counter += 1
        rider = Rider(self.rider_id_counter)
        rider.speed = self.rider_speed
        self.funds -= self.rider_recruitment_cost
        self.riders.append(rider)
        LOGGER.info("Recruited rider %s (funds now %s)", rider.rider_id, self.funds)
        return rider

    def submit_order(self, res_pos, cus_pos) -> dict:
        """Create an order, recruit if necessary, assign it and plan its route.

        Args:
            res_pos: Restaurant coordinates (x, y).
            cus_pos: Customer coordinates (x, y).

        Returns:
            dict: Keys ``order`` (Order), ``rider`` (Rider), ``new_rider``
            (bool) and ``route`` (Route).

        Raises:
            ValueError: If coordinates are invalid.
            RuntimeError: If no rider is available and none can be recruited.
        """
        order: Order = self.order_manager.create_order(res_pos, cus_pos, self.current_tick)
        new_rider = False
        try:
            if not self.has_idle_rider() and self.recruit_rider() is not None:
                new_rider = True
            if not self.riders:
                raise RuntimeError("No riders available and insufficient funds to recruit one.")
            rider = self.order_manager.assign_order(order)
            if rider is None:
                raise RuntimeError("No rider could accept the order.")
        except Exception:
            self.order_manager.discard(order)
            raise
        route: Route = self.planner.plan_multi(
            rider.position, [order.res_pos, order.cus_pos], rider.speed
        )
        LOGGER.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return {"order": order, "rider": rider, "new_rider": new_rider, "route": route}

    def tick(self) -> List[str]:
        """Advance the simulation by one tick.

        Returns:
            List[str]: Consistency issues detected (and repaired) this tick.
        """
        self.current_tick += 1
        globalvar.set_value("current_tick", self.current_tick)
        for rider in list(self.riders):
            rider.move()
        return self.check_consistency()

    def run_ticks(self, count: int) -> List[str]:
        """Advance the simulation several ticks.

        Args:
            count: Number of ticks to run.

        Returns:
            List[str]: All consistency issues found during the run.
        """
        issues: List[str] = []
        for _ in range(count):
            issues.extend(self.tick())
        return issues

    def check_consistency(self) -> List[str]:
        """Verify and repair internal state consistency.

        Returns:
            List[str]: Human readable descriptions of issues found.
        """
        issues: List[str] = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)
            if rider.state == STATE_IDLE and rider.orders:
                issues.append(f"rider {rider.rider_id} idle with orders; repairing")
                rider._recover()
            completed = [o for o in rider.orders if o.is_completed()]
            if completed:
                issues.append(f"rider {rider.rider_id} holds completed orders; removing")
                rider.orders = [o for o in rider.orders if not o.is_completed()]
        if len(self.riders) > self.max_riders:
            issues.append("rider count exceeds configured maximum")
        for message in issues:
            LOGGER.warning(message)
        return issues

    def snapshot(self) -> dict:
        """Return a JSON-compatible snapshot of the whole simulation.

        Returns:
            dict: Funds, clock, rider and order data.
        """
        return {
            "funds": self.funds,
            "current_tick": self.current_tick,
            "rider_id_counter": self.rider_id_counter,
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.order_manager.orders],
        }

    def shutdown(self) -> None:
        """Stop the main loop.

        Returns:
            None
        """
        self.running_state = False


def init_system(parameters: Optional[Dict] = None) -> SystemManager:
    """Reset global state and create a ready-to-use system manager.

    Args:
        parameters: Optional parameter overrides.

    Returns:
        SystemManager: The initialized system.
    """
    globalvar._init()
    return SystemManager(parameters)
