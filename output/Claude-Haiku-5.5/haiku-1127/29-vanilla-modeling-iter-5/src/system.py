"""System-level state management and simulation tick loop.

``SystemManager`` owns funds, the rider id counter, the running flag and the
order manager. ``init_system`` resets global storage, loads configuration and
returns a ready-to-use manager.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import config
import globalvar
from order import OrderManager
from order_model import STATUS_COMPLETED
from rider import STATE_IDLE, Rider

logger = logging.getLogger(__name__)


class SystemManager:
    """Core coordinator for funds, riders, orders and the simulated clock.

    Attributes:
        funds: Current system funds (may be negative).
        rider_id_counter: Last assigned rider id.
        is_running: Main loop control flag.
        order_manager: The OrderManager instance.
    """

    def __init__(self) -> None:
        """Create the manager with configured initial funds."""
        self.funds: int = int(config.CONFIG["initial_funds"])
        self.rider_id_counter: int = 0
        self.is_running: bool = True
        self.order_manager = OrderManager()
        globalvar.set_value("riders", [])
        globalvar.set_value("current_tick", 0)

    @property
    def riders(self) -> List[Rider]:
        """The rider list stored under the global key 'riders'."""
        return globalvar.get_value("riders") or []

    @property
    def current_tick(self) -> int:
        """Current simulation tick."""
        return int(globalvar.get_value("current_tick") or 0)

    def find_rider(self, rider_id: Optional[int]) -> Optional[Rider]:
        """Look up a rider by identifier.

        Args:
            rider_id: Rider identifier.

        Returns:
            The matching Rider or None.
        """
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def create_rider(self) -> Rider:
        """Create a new idle rider and add it to the rider list.

        Returns:
            The created Rider.
        """
        self.rider_id_counter += 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        logger.info("rider %s recruited", rider.rider_id)
        return rider

    def idle_rider_count(self) -> int:
        """Count riders with state idle and no assigned orders.

        Returns:
            Number of available riders.
        """
        return sum(1 for r in self.riders if r.state == STATE_IDLE and not r.orders)

    def can_recruit(self) -> bool:
        """Check the recruitment trigger.

        Returns:
            True when funds are at least the recruitment threshold and the
            number of pending orders exceeds the number of idle riders.
        """
        threshold = int(config.CONFIG["recruit_min_funds"])
        return (
            self.funds >= threshold
            and self.order_manager.pending_count > self.idle_rider_count()
        )

    def recruit_riders(self) -> int:
        """Recruit riders while the recruitment trigger holds.

        Each recruit costs ``rider_cost`` from system funds.

        Returns:
            Number of riders added.
        """
        added = 0
        cost = int(config.CONFIG["rider_cost"])
        while self.can_recruit():
            self.funds -= cost
            self.create_rider()
            added += 1
        return added

    def submit_order(self, res_pos, cus_pos):
        """Create an order, recruit if needed and attempt assignment.

        Args:
            res_pos: Restaurant point ``(x, y)``.
            cus_pos: Customer point ``(x, y)``.

        Returns:
            The created Order (status is 'assigned' or 'pending').
        """
        order = self.order_manager.create_order(res_pos, cus_pos)
        self.recruit_riders()
        self.order_manager.assign_pending_orders()
        return order

    def check_consistency(self) -> List[str]:
        """Verify and automatically repair state inconsistencies.

        Returns:
            Descriptions of the issues found (empty when consistent).
        """
        issues: List[str] = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)
            completed = [o for o in rider.orders if o.status == STATUS_COMPLETED]
            if completed:
                issues.append(f"rider {rider.rider_id} held completed orders; removed")
                rider.orders = [o for o in rider.orders if o.status != STATUS_COMPLETED]
            if not rider.orders and rider.state != STATE_IDLE:
                issues.append(f"rider {rider.rider_id} had no orders but was not idle; reset")
                rider.state = STATE_IDLE
                rider.reset_route()
        return issues

    def tick(self) -> None:
        """Advance the simulation by one tick.

        Order of operations: increment clock, recruit riders, assign pending
        orders, move every rider, and run consistency checks.
        """
        globalvar.set_value("current_tick", self.current_tick + 1)
        self.recruit_riders()
        self.order_manager.assign_pending_orders()
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # error recovery: keep the simulation running
                logger.exception("rider %s failed to move; resetting route", rider.rider_id)
                rider.reset_route()
        for issue in self.check_consistency():
            logger.warning(issue)

    def shutdown(self) -> None:
        """Stop the main loop."""
        self.is_running = False

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the system.

        Returns:
            Dictionary with funds, counters, riders and order history.
        """
        return {
            "funds": self.funds,
            "rider_id_counter": self.rider_id_counter,
            "current_tick": self.current_tick,
            "is_running": self.is_running,
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.all_orders],
        }

    def save_state(self, path: Optional[str] = None) -> str:
        """Write the system snapshot to a JSON file.

        Args:
            path: Destination path; defaults to the configured state file.

        Returns:
            The path that was written.
        """
        target = path or str(config.CONFIG["state_file"])
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
        return target


def init_system(config_path: Optional[str] = None) -> SystemManager:
    """Initialise global storage, configuration and the system manager.

    Args:
        config_path: Optional path to a JSON configuration file.

    Returns:
        A ready SystemManager instance.
    """
    globalvar._init()
    config.load_config(config_path)
    return SystemManager()
