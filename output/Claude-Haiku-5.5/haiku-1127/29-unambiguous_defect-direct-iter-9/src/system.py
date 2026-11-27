"""System manager: funds, rider roster, simulated clock and consistency checks."""

import logging
from typing import Any, Dict, List, Optional

import globalvar
from config import (
    CELL_SIZE,
    DEFAULT_PARAMS,
    GRID_DIM,
    STATE_IDLE,
    cell_center,
    param,
)
from rider import Rider

logger = logging.getLogger("dispatch.system")


def build_grid() -> List[List[tuple]]:
    """Build the 8x8 grid map with each cell's centre point.

    Returns:
        A list of 8 rows; each row contains 8 ``(center_x, center_y)`` tuples.
    """
    return [[cell_center(col * CELL_SIZE, row * CELL_SIZE)
             for col in range(GRID_DIM)] for row in range(GRID_DIM)]


class SystemManager:
    """Owns system-wide state: funds, riders, clock and run flag.

    All state lives in the ``globalvar`` store under the keys ``funds``,
    ``riders``, ``rider_counter``, ``running``, ``tick``, ``orders`` and
    ``grid``.
    """

    def __init__(self, params: Optional[Dict[str, int]] = None) -> None:
        """Initialise the global state.

        Args:
            params: Optional parameter overrides merged over the defaults.
        """
        if params:
            globalvar.set_value("params", dict(params))
        globalvar.set_value("funds", param("initial_funds"))
        globalvar.set_value("riders", [])
        globalvar.set_value("rider_counter", 0)
        globalvar.set_value("running", True)
        globalvar.set_value("tick", 0)
        globalvar.set_value("orders", [])
        globalvar.set_value("grid", build_grid())
        logger.info("System initialised with funds %s", self.funds)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    @property
    def funds(self) -> int:
        """Current system fund balance (may be negative)."""
        return globalvar.get_value("funds", 0)

    @property
    def riders(self) -> List[Rider]:
        """The rider roster (live list)."""
        return globalvar.get_value("riders", [])

    @property
    def tick_count(self) -> int:
        """Current simulated time."""
        return globalvar.get_value("tick", 0)

    def add_funds(self, amount: int) -> None:
        """Adjust the fund balance by ``amount`` (negative to spend)."""
        globalvar.set_value("funds", self.funds + int(amount))

    def get_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with ``rider_id`` or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def is_running(self) -> bool:
        """Return the main loop run flag."""
        return bool(globalvar.get_value("running", False))

    def stop(self) -> None:
        """Request the main loop to terminate."""
        globalvar.set_value("running", False)

    # ------------------------------------------------------------------
    # Rider lifecycle
    # ------------------------------------------------------------------
    def recruit_rider(self) -> Optional[Rider]:
        """Recruit a new rider if the roster has room and funds cover the cost.

        Returns:
            The new ``Rider`` or None if recruitment was not possible.
        """
        if len(self.riders) >= param("max_riders"):
            logger.info("Recruitment skipped: roster is full")
            return None
        cost = param("recruit_cost")
        if self.funds < cost:
            logger.info("Recruitment skipped: insufficient funds (%s < %s)",
                        self.funds, cost)
            return None
        self.add_funds(-cost)
        rider_id = globalvar.get_value("rider_counter", 0) + 1
        globalvar.set_value("rider_counter", rider_id)
        rider = Rider(rider_id)
        self.riders.append(rider)
        logger.info("Recruited rider %s for %s", rider_id, cost)
        return rider

    def remove_rider(self, rider_id: int) -> bool:
        """Remove an idle rider from the roster.

        Args:
            rider_id: Identifier of the rider to remove.

        Returns:
            True if removed, False if the rider does not exist.

        Raises:
            ValueError: If the rider still has assigned orders.
        """
        rider = self.get_rider(rider_id)
        if rider is None:
            return False
        if rider.orders:
            raise ValueError(f"rider {rider_id} still has {len(rider.orders)} order(s)")
        self.riders.remove(rider)
        return True

    # ------------------------------------------------------------------
    # Simulation clock
    # ------------------------------------------------------------------
    def tick(self) -> List[Dict[str, Any]]:
        """Advance the simulation by one time unit.

        Every rider moves once, upkeep is charged, and the clock increments.

        Returns:
            Event log entries produced during this tick.
        """
        events: List[Dict[str, Any]] = []
        for rider in list(self.riders):
            before = len(rider.log)
            rider.move()
            events.extend(rider.log[before:])
        globalvar.set_value("tick", self.tick_count + 1)
        self.add_funds(-param("upkeep_per_rider") * len(self.riders))
        return events

    # ------------------------------------------------------------------
    # Consistency and recovery
    # ------------------------------------------------------------------
    def consistency_check(self) -> List[str]:
        """Verify and repair the rider/order state.

        Repairs performed:
          * Riders that are active without orders are reset to idle.
          * Completed or rejected orders are removed from rider queues.
          * Duplicate rider IDs are reported.

        Returns:
            Human-readable list of issues found (empty when consistent).
        """
        issues: List[str] = []
        seen = set()
        for rider in self.riders:
            if rider.rider_id in seen:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen.add(rider.rider_id)
            if rider.state != STATE_IDLE and not rider.orders:
                issues.append(f"rider {rider.rider_id} active without orders; reset")
                rider.state = STATE_IDLE
                rider.path = []
                rider.special_case = False
            stale = [o for o in rider.orders if o.status in ("completed", "rejected")]
            if stale:
                issues.append(f"rider {rider.rider_id} held {len(stale)} finished order(s); removed")
                rider.orders = [o for o in rider.orders if o not in stale]
        if issues:
            logger.warning("Consistency check: %s", "; ".join(issues))
        return issues

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the whole system."""
        return {
            "params": {key: param(key) for key in DEFAULT_PARAMS},
            "funds": self.funds,
            "tick": self.tick_count,
            "rider_counter": globalvar.get_value("rider_counter", 0),
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in globalvar.get_value("orders", [])],
        }


def init_system(params: Optional[Dict[str, int]] = None) -> SystemManager:
    """Reset the global store and create the system manager.

    Args:
        params: Optional parameter overrides.

    Returns:
        The initialised ``SystemManager``.
    """
    globalvar._init()
    manager = SystemManager(params)
    globalvar.set_value("system", manager)
    return manager


def get_system() -> SystemManager:
    """Return the active system manager, initialising one if needed."""
    manager = globalvar.get_value("system")
    if manager is None:
        manager = init_system()
    return manager
