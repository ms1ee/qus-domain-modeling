"""System-level state management: funds, riders, ticks and recovery."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from config import DEFAULT_SETTINGS, LOGGER
from order import OrderManager
from order_model import Order
from rider import IDLE, Rider


class SystemManager:
    """Core controller for funds, riders, orders and the simulation clock.

    Funds, rider list, counters and the running flag are stored in the
    ``globalvar`` store so that all modules observe the same values.

    Attributes:
        settings: Effective system parameters.
        order_manager: Owner of all orders.
    """

    def __init__(self, settings: Optional[Dict[str, Any]] = None) -> None:
        """Create the manager on top of an already-initialised global store.

        Args:
            settings: System parameters; missing keys use defaults.
        """
        self.settings: Dict[str, Any] = {**DEFAULT_SETTINGS, **(settings or {})}
        self.order_manager = OrderManager()

    @property
    def funds(self) -> int:
        """Current system funds (may be negative)."""
        return int(globalvar.get_value("funds") or 0)

    @funds.setter
    def funds(self, value: int) -> None:
        globalvar.set_value("funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """Dynamic list of all riders."""
        return globalvar.get_value("riders")

    @property
    def rider_id_counter(self) -> int:
        """Last rider identifier handed out."""
        return int(globalvar.get_value("rider_id_counter") or 0)

    @property
    def current_tick(self) -> int:
        """Current simulation tick."""
        return int(globalvar.get_value("current_tick") or 0)

    @current_tick.setter
    def current_tick(self, value: int) -> None:
        globalvar.set_value("current_tick", int(value))

    @property
    def is_running(self) -> bool:
        """Whether the main loop should continue."""
        return bool(globalvar.get_value("is_running"))

    @is_running.setter
    def is_running(self, value: bool) -> None:
        globalvar.set_value("is_running", bool(value))

    def idle_riders(self) -> List[Rider]:
        """Return riders that are idle and have no assigned orders."""
        return [r for r in self.riders if r.state == IDLE and not r.orders]

    def rider_by_id(self, rider_id: Optional[int]) -> Optional[Rider]:
        """Look up a rider by identifier."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def recruit_rider(self) -> Optional[Rider]:
        """Create a new rider if funds allow.

        Deducts the recruit cost and assigns the next auto-incremented ID.

        Returns:
            The new rider, or ``None`` if funds are below the threshold.
        """
        threshold = int(self.settings["recruit_threshold"])
        cost = int(self.settings["recruit_cost"])
        if self.funds < threshold or self.funds < cost:
            return None
        self.funds = self.funds - cost
        new_id = self.rider_id_counter + 1
        globalvar.set_value("rider_id_counter", new_id)
        rider = Rider(new_id)
        self.riders.append(rider)
        LOGGER.info("Recruited rider %d; funds now %d", new_id, self.funds)
        return rider

    def maybe_recruit(self, pending_count: int) -> int:
        """Recruit riders while pending orders exceed idle riders.

        Args:
            pending_count: Number of orders waiting for a rider.

        Returns:
            Number of riders recruited.
        """
        added = 0
        while pending_count > len(self.idle_riders()):
            if self.recruit_rider() is None:
                break
            added += 1
        return added

    def dispatch(self) -> int:
        """Assign pending orders to riders, recruiting when necessary.

        Returns:
            Number of orders assigned.
        """
        return len(self.order_manager.dispatch_pending(self.maybe_recruit))

    def submit_order(self, res_pos, cus_pos) -> Tuple[Order, Optional[Rider], bool]:
        """Create an order from user input and dispatch it immediately.

        Args:
            res_pos: Restaurant ``(x, y)``.
            cus_pos: Customer ``(x, y)``.

        Returns:
            Tuple ``(order, rider, rider_added)`` where ``rider`` is ``None``
            if the order remains pending and ``rider_added`` reports whether a
            new rider was recruited for this order.
        """
        before = len(self.riders)
        order = self.order_manager.create_order(res_pos, cus_pos)
        self.dispatch()
        rider = self.rider_by_id(order.rider_id)
        return order, rider, len(self.riders) > before

    def tick(self) -> None:
        """Advance the simulation by one unit of time.

        Increments the clock, dispatches pending orders and moves every rider.
        """
        self.current_tick = self.current_tick + 1
        self.dispatch()
        for rider in list(self.riders):
            rider.move()

    def check_consistency(self) -> List[str]:
        """Detect and repair inconsistent state.

        Repairs riders stuck in a working state without orders, clears stale
        paths, removes completed orders from rider queues and removes assigned
        orders from the pending queue.

        Returns:
            Human-readable descriptions of the repairs performed.
        """
        issues: List[str] = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)
            completed = [o for o in rider.orders if o.is_completed()]
            if completed:
                rider.orders = [o for o in rider.orders if not o.is_completed()]
                issues.append(f"removed completed orders from rider {rider.rider_id}")
            if rider.state != IDLE and not rider.orders:
                rider.state = IDLE
                rider.path = []
                issues.append(f"reset rider {rider.rider_id} to idle")
            if rider.state == IDLE and rider.path:
                rider.path = []
                issues.append(f"cleared stale path of rider {rider.rider_id}")
        before = len(self.order_manager.pending)
        self.order_manager.pending = [
            o for o in self.order_manager.pending if o.rider_id is None
        ]
        if len(self.order_manager.pending) != before:
            issues.append("removed assigned orders from pending queue")
        for issue in issues:
            LOGGER.warning("Consistency repair: %s", issue)
        return issues

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of configuration, riders and orders."""
        return {
            "settings": dict(self.settings),
            "funds": self.funds,
            "current_tick": self.current_tick,
            "rider_id_counter": self.rider_id_counter,
            "riders": [rider.to_dict() for rider in self.riders],
            "pending_order_ids": [o.id for o in self.order_manager.pending],
            "orders": [o.to_dict() for o in self.order_manager.history],
        }


def init_system(settings: Optional[Dict[str, Any]] = None) -> SystemManager:
    """Initialise the global store and create the system manager.

    Sets funds to the configured initial value, an empty rider list, zero
    counters, the running flag to True and the simulated time to zero.

    Args:
        settings: Optional system parameters (see ``config.DEFAULT_SETTINGS``).

    Returns:
        The initialised ``SystemManager``.
    """
    effective = {**DEFAULT_SETTINGS, **(settings or {})}
    globalvar._init()
    globalvar.set_value("funds", int(effective["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("is_running", True)
    globalvar.set_value("current_tick", 0)
    globalvar.set_value("order_id_counter", 0)
    globalvar.set_value("rider_speed", int(effective["rider_speed"]))
    globalvar.set_value(
        "rider_start",
        (int(effective["rider_start_x"]), int(effective["rider_start_y"])),
    )
    globalvar.set_value("recruit_cost", int(effective["recruit_cost"]))
    globalvar.set_value("recruit_threshold", int(effective["recruit_threshold"]))
    return SystemManager(effective)
