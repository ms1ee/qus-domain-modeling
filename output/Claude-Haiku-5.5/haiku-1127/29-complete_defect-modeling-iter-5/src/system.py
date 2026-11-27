"""System manager: funds, rider recruitment, clock and persistence."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from typing import Any, Dict, List, Tuple

import globalvar
from config import SystemConfig, get_config
from globalvar import get_value, set_value
from order import OrderManager
from order_model import Order
from rider import STATE_IDLE, STATE_PICKING_UP, Rider

logger = logging.getLogger(__name__)


class SystemManager:
    """Core coordinator for funds, riders, orders and the simulated clock.

    State is kept in the global store so that every module sees the same
    values. Properties on this class read and write those globals.
    """

    def __init__(self, config: SystemConfig = None) -> None:
        """Create the manager.

        Args:
            config: Configuration to use. Defaults to the active configuration.
        """
        self.config = config or get_config()
        self.order_manager = OrderManager()

    @property
    def funds(self) -> int:
        """System funds (integer, may be negative)."""
        return int(get_value("funds", 0) or 0)

    @funds.setter
    def funds(self, value: int) -> None:
        set_value("funds", int(value))

    @property
    def rider_id_counter(self) -> int:
        """Last rider ID handed out."""
        return int(get_value("rider_id_counter", 0) or 0)

    @rider_id_counter.setter
    def rider_id_counter(self, value: int) -> None:
        set_value("rider_id_counter", int(value))

    @property
    def is_running(self) -> bool:
        """Whether the main loop should keep running."""
        return bool(get_value("is_running", True))

    @is_running.setter
    def is_running(self, value: bool) -> None:
        set_value("is_running", bool(value))

    @property
    def current_tick(self) -> int:
        """Current simulated time."""
        return int(get_value("current_tick", 0) or 0)

    @current_tick.setter
    def current_tick(self, value: int) -> None:
        set_value("current_tick", int(value))

    @property
    def riders(self) -> List[Rider]:
        """The dynamic list of riders."""
        riders = get_value("riders")
        if riders is None:
            riders = []
            set_value("riders", riders)
        return riders

    def add_funds(self, amount: int) -> List[Rider]:
        """Add funds (may be negative) and recruit riders when affordable.

        Args:
            amount: Amount to add to the system funds.

        Returns:
            Riders recruited as a consequence of this change.
        """
        self.funds = self.funds + int(amount)
        return self.check_recruitment()

    def check_recruitment(self) -> List[Rider]:
        """Recruit riders while funds are at or above the threshold.

        Returns:
            The list of newly recruited riders.
        """
        recruited: List[Rider] = []
        while (self.funds >= self.config.recruitment_threshold
               and self.config.recruitment_cost > 0):
            self.funds = self.funds - self.config.recruitment_cost
            recruited.append(self.recruit_rider())
        return recruited

    def recruit_rider(self) -> Rider:
        """Create a new idle rider with a unique ID and add it to the list.

        Returns:
            The newly created Rider.
        """
        self.rider_id_counter = self.rider_id_counter + 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        logger.info("Recruited rider #%d", rider.rider_id)
        return rider

    def create_order(self, res_pos: Tuple[int, int], cus_pos: Tuple[int, int]
                     ) -> Tuple[Order, List[Rider]]:
        """Accept a new order, credit its fee, recruit and dispatch.

        Args:
            res_pos: Restaurant coordinates (x, y).
            cus_pos: Customer coordinates (x, y).

        Returns:
            Tuple of the created Order and the list of recruited riders.

        Raises:
            ValueError: If the coordinates are invalid.
        """
        order = self.order_manager.create_order(res_pos, cus_pos)
        new_riders = self.add_funds(self.config.order_fee)
        self.dispatch()
        return order, new_riders

    def dispatch(self) -> List[Order]:
        """Assign pending orders to the best available riders.

        Returns:
            Orders assigned during this dispatch round.
        """
        return self.order_manager.assign_pending()

    def tick(self, count: int = 1) -> int:
        """Advance the simulation by ``count`` ticks.

        Each tick increments the clock, moves every rider, and then dispatches
        pending orders.

        Args:
            count: Number of ticks to simulate.

        Returns:
            The simulated time after advancing.
        """
        for _ in range(max(int(count), 0)):
            self.current_tick = self.current_tick + 1
            for rider in list(self.riders):
                rider.move()
            self.dispatch()
        return self.current_tick

    def shutdown(self) -> None:
        """Stop the main loop."""
        self.is_running = False

    def verify_state(self) -> List[str]:
        """Check system consistency and repair problems where possible.

        Returns:
            Human-readable descriptions of issues found and repaired.
        """
        issues: List[str] = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                issues.append(f"duplicate rider id #{rider.rider_id}")
            seen_ids.add(rider.rider_id)
            repair = rider.resync()
            if repair:
                issues.append(repair)
        pending = get_value("pending_orders") or []
        for order in list(pending):
            if order.status != Order.STATUS_PENDING:
                issues.append(f"order #{order.id} in pending queue with status {order.status}")
                pending.remove(order)
        for issue in issues:
            logger.warning("State check: %s", issue)
        return issues

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the whole system.

        Returns:
            Dictionary with configuration, funds, riders and orders.
        """
        return {
            "config": asdict(self.config),
            "funds": self.funds,
            "current_tick": self.current_tick,
            "rider_id_counter": self.rider_id_counter,
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in get_value("orders") or []],
            "pending_order_ids": [o.id for o in get_value("pending_orders") or []],
        }

    def save_history(self, path: str = None) -> str:
        """Persist the system snapshot to a JSON file atomically.

        Args:
            path: Target file. Defaults to the configured history file.

        Returns:
            The path that was written.

        Raises:
            OSError: If the file cannot be written.
        """
        target = path or self.config.history_file
        temp = target + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(self.snapshot(), handle, indent=2)
        os.replace(temp, target)
        logger.info("History saved to %s", target)
        return target


def init_system() -> SystemManager:
    """Initialise global state and create the system manager.

    Resets the global store, loads the active configuration, sets the
    starting funds and recruits riders if the starting funds already meet the
    recruitment threshold.

    Returns:
        The initialised SystemManager.
    """
    globalvar._init()
    cfg = get_config()
    set_value("config", cfg)
    set_value("funds", int(cfg.initial_funds))
    manager = SystemManager(cfg)
    set_value("system", manager)
    manager.check_recruitment()
    logger.info("System initialised with funds %d", manager.funds)
    return manager
