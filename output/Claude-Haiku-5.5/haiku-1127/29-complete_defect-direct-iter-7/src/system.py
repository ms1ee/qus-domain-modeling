"""System management: global initialisation, funds, recruitment and ticks."""

from __future__ import annotations

import logging

import config
import globalvar
from order import OrderManager
from order_model import (
    STATUS_CREATED,
    STATUS_DELIVERING,
    STATUS_PICKING_UP,
)
from rider import STATE_IDLE, Rider

logger = logging.getLogger("dispatch.system")


def init_system() -> None:
    """Initialise the global variables and the grid description.

    Sets the rider list to empty, the rider id counter to 0, the running
    flag to True, funds to 0, and describes the 8x8 grid map.
    """
    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("funds", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("pending_orders", [])
    globalvar.set_value("grid", {
        "map_size": config.MAP_SIZE,
        "cell_size": config.CELL_SIZE,
        "grid_size": config.GRID_SIZE,
    })
    logger.info("System initialised")


class SystemManager:
    """Owns funds, the rider roster and the simulation clock."""

    def __init__(self) -> None:
        """Initialise global state and the order manager."""
        init_system()
        self.order_manager = OrderManager()

    # ------------------------------------------------------------------
    # Funds and state accessors
    # ------------------------------------------------------------------
    @property
    def funds(self) -> int:
        """Current system funds (may be negative)."""
        return int(globalvar.get_value("funds", 0))

    def add_funds(self, amount: int) -> None:
        """Add (or subtract, with a negative amount) system funds.

        Args:
            amount: Integer amount to add.
        """
        globalvar.set_value("funds", self.funds + int(amount))

    @property
    def riders(self) -> list[Rider]:
        """The live list of riders."""
        return globalvar.get_value("riders", [])

    @property
    def tick(self) -> int:
        """Current simulated tick."""
        return int(globalvar.get_value("tick", 0))

    @property
    def running(self) -> bool:
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("running", True))

    def stop(self) -> None:
        """Request the main loop to terminate."""
        globalvar.set_value("running", False)

    def get_rider(self, rider_id: int) -> Rider | None:
        """Look up a rider by id.

        Args:
            rider_id: Identifier to find.

        Returns:
            Rider or None.
        """
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    # ------------------------------------------------------------------
    # Rider CRUD and recruitment
    # ------------------------------------------------------------------
    def spawn_rider(self, x: int | None = None,
                    y: int | None = None) -> Rider:
        """Create a new idle rider with the next unique id.

        Without explicit coordinates, riders are spread over the cell
        centres of the grid in order of recruitment.

        Args:
            x: Optional initial x coordinate.
            y: Optional initial y coordinate.

        Returns:
            Rider: The newly created rider.
        """
        riders = self.riders
        if x is None or y is None:
            half = config.CELL_SIZE // 2
            index = len(riders)
            x = (index % config.GRID_SIZE) * config.CELL_SIZE + half
            y = ((index // config.GRID_SIZE) % config.GRID_SIZE) \
                * config.CELL_SIZE + half
        rider_id = int(globalvar.get_value("rider_id_counter", 0)) + 1
        globalvar.set_value("rider_id_counter", rider_id)
        rider = Rider(rider_id, x, y)
        riders.append(rider)
        logger.info("Recruited rider %d", rider_id)
        return rider

    def remove_rider(self, rider_id: int) -> None:
        """Remove an idle rider from the roster.

        Args:
            rider_id: Identifier of the rider to remove.

        Raises:
            ValueError: If the rider does not exist or is busy.
        """
        rider = self.get_rider(rider_id)
        if rider is None:
            raise ValueError(f"rider #{rider_id} does not exist")
        if rider.state != STATE_IDLE or rider.orders:
            raise ValueError(f"rider #{rider_id} is busy and cannot be removed")
        self.riders.remove(rider)
        logger.info("Removed rider %d", rider_id)

    def check_recruitment(self) -> list[Rider]:
        """Recruit riders while funds are at or above the threshold.

        Each recruitment deducts RIDER_COST from the funds.

        Returns:
            list[Rider]: Riders recruited by this call (possibly empty).
        """
        recruited = []
        while self.funds >= config.RECRUIT_THRESHOLD:
            self.add_funds(-config.RIDER_COST)
            recruited.append(self.spawn_rider())
        return recruited

    # ------------------------------------------------------------------
    # Simulation clock
    # ------------------------------------------------------------------
    def advance_tick(self) -> list[dict]:
        """Advance the simulation by one tick.

        Every rider moves once, queued orders are assigned if riders have
        become available, and state consistency is checked.  Errors raised
        by a single rider are contained and the rider is recovered.

        Returns:
            list[dict]: Event records produced during the tick.
        """
        globalvar.set_value("tick", self.tick + 1)
        events: list[dict] = []
        for rider in list(self.riders):
            try:
                events.extend(rider.move())
            except Exception:  # noqa: BLE001 - recovery must not stop the loop
                logger.exception("Rider %d failed; recovering", rider.rider_id)
                try:
                    rider.recover()
                except Exception:  # noqa: BLE001
                    logger.exception("Recovery failed for rider %d",
                                     rider.rider_id)
                    rider.state = STATE_IDLE
                    rider.waypoints = []
                events.append({
                    "event": "recovered", "order_id": None,
                    "rider_id": rider.rider_id, "tick": self.tick,
                })
        try:
            for order, rider in self.order_manager.assign_pending():
                events.append({
                    "event": "assigned", "order_id": order.id,
                    "rider_id": rider.rider_id, "tick": self.tick,
                })
        except Exception:  # noqa: BLE001
            logger.exception("Assignment of queued orders failed")
        for issue in self.check_consistency():
            logger.warning("Consistency: %s", issue)
        return events

    def check_consistency(self) -> list[str]:
        """Check and, where safe, repair the global system state.

        Returns:
            list[str]: Human-readable descriptions of issues found.
        """
        issues: list[str] = []
        if not isinstance(globalvar.get_value("funds", 0), int):
            issues.append("funds is not an integer; reset to 0")
            globalvar.set_value("funds", 0)
        seen: set[int] = set()
        for rider in self.riders:
            if rider.rider_id in seen:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen.add(rider.rider_id)
            if len(rider.orders) > config.MAX_ORDERS_PER_RIDER:
                issues.append(
                    f"rider #{rider.rider_id} holds {len(rider.orders)} orders")
            if rider.state != STATE_IDLE and not rider.orders:
                issues.append(
                    f"rider #{rider.rider_id} was busy without orders; reset")
                rider.state = STATE_IDLE
                rider.waypoints = []
                rider.special_case = False
            if rider.state == STATE_IDLE and any(
                    o.status in (STATUS_PICKING_UP, STATUS_DELIVERING)
                    for o in rider.orders):
                issues.append(
                    f"rider #{rider.rider_id} is idle with an active order")
        for order in self.order_manager.pending_orders():
            if order.status != STATUS_CREATED:
                issues.append(
                    f"queued order #{order.id} has status {order.status}")
        return issues
