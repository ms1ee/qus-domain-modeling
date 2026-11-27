"""System manager: funds, rider pool, recruitment and simulation clock."""

import logging
from typing import Any, Dict, List, Optional

import globalvar
from config import DEFAULT_CONFIG
from path_planner import MAP_SIZE
from rider import DELIVERING, IDLE, PICKING_UP, Rider

logger = logging.getLogger(__name__)


class SystemManager:
    """Owns the system funds, the rider pool and the simulation clock.

    Attributes:
        initial_funds: Starting funds.
        recruit_cost: Cost deducted for each recruited rider.
        recruit_threshold: Minimum funds needed to recruit.
        rider_speed: Speed given to newly recruited riders.
        funds: Current funds (may be negative).
        rider_id_counter: Last issued rider id.
        is_running: Controls the main loop.
        current_tick: Simulation clock.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Create the system manager with the given or default parameters.

        Args:
            config: Optional overrides for the keys in ``DEFAULT_CONFIG``.
        """
        settings = dict(DEFAULT_CONFIG)
        settings.update(config or {})
        self.initial_funds = int(settings["initial_funds"])
        self.recruit_cost = int(settings["recruit_cost"])
        self.recruit_threshold = int(settings["recruit_threshold"])
        self.rider_speed = int(settings["rider_speed"])
        self.funds = self.initial_funds
        self.rider_id_counter = 0
        self.is_running = True
        self.current_tick = 0
        globalvar.set_value("current_tick", 0)

    @property
    def riders(self) -> List[Rider]:
        """Return the live rider list stored in the global variables."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    def idle_riders(self) -> List[Rider]:
        """Return riders in the idle state."""
        return [rider for rider in self.riders if rider.state == IDLE]

    def create_rider(self) -> Rider:
        """Recruit a new rider, deducting the recruitment cost.

        Returns:
            The newly created rider.
        """
        self.rider_id_counter += 1
        rider = Rider(self.rider_id_counter, speed=self.rider_speed)
        self.funds -= self.recruit_cost
        self.riders.append(rider)
        logger.info("Recruited rider %d (funds now %d)", rider.rider_id, self.funds)
        return rider

    def maybe_recruit(self, pending_count: int) -> List[Rider]:
        """Recruit riders while funds allow and pending orders outnumber idle riders.

        Args:
            pending_count: Number of pending (unassigned) orders.

        Returns:
            List of riders created by this call.
        """
        created: List[Rider] = []
        while (self.funds >= self.recruit_threshold
               and pending_count > len(self.idle_riders())):
            created.append(self.create_rider())
        return created

    def remove_rider(self, rider_id: int) -> bool:
        """Remove an idle rider from the pool.

        Args:
            rider_id: Id of the rider to remove.

        Returns:
            True if the rider was removed, False otherwise.
        """
        for rider in self.riders:
            if rider.rider_id == rider_id:
                if rider.state != IDLE or rider.orders:
                    return False
                self.riders.remove(rider)
                return True
        return False

    def tick(self) -> None:
        """Advance the simulation by one unit of time.

        Increments the clock and moves every rider. Exceptions raised by a
        single rider are logged and that rider's state is repaired.
        """
        self.current_tick += 1
        globalvar.set_value("current_tick", self.current_tick)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # noqa: BLE001 - keep the simulation running
                logger.exception("Rider %d failed during tick", rider.rider_id)
                self._repair_rider(rider)

    @staticmethod
    def _repair_rider(rider: Rider) -> bool:
        """Bring a rider's state in line with its order list.

        Args:
            rider: Rider to repair.

        Returns:
            True if a change was made.
        """
        changed = False
        if rider.orders and rider.state == IDLE:
            rider.state = PICKING_UP
            changed = True
        elif not rider.orders and rider.state != IDLE:
            rider.state = IDLE
            rider.special_case = False
            changed = True
        if rider.state not in (IDLE, PICKING_UP, DELIVERING):
            rider.state = IDLE if not rider.orders else PICKING_UP
            changed = True
        return changed

    def repair_state(self) -> int:
        """Repair inconsistent rider states across the whole pool.

        Returns:
            Number of riders whose state was corrected.
        """
        return sum(1 for rider in self.riders if self._repair_rider(rider))

    def check_consistency(self) -> List[str]:
        """Check the system state and return a list of problems found.

        Returns:
            Human-readable issue descriptions; empty when consistent.
        """
        issues: List[str] = []
        for rider in self.riders:
            if rider.state == IDLE and rider.orders:
                issues.append(f"Rider #{rider.rider_id} is idle but has orders")
            if rider.state != IDLE and not rider.orders:
                issues.append(f"Rider #{rider.rider_id} is busy without orders")
            if rider.speed <= 0:
                issues.append(f"Rider #{rider.rider_id} has invalid speed")
            if not (0 <= rider.x <= MAP_SIZE and 0 <= rider.y <= MAP_SIZE):
                issues.append(f"Rider #{rider.rider_id} is outside the map")
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    issues.append(
                        f"Order #{order.id} is held by rider #{rider.rider_id} "
                        f"but recorded for rider #{order.rider_id}")
        return issues

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the system state."""
        return {
            "funds": self.funds,
            "current_tick": self.current_tick,
            "rider_id_counter": self.rider_id_counter,
            "riders": [rider.to_dict() for rider in self.riders],
        }

    def shutdown(self) -> None:
        """Stop the main loop."""
        self.is_running = False


def init_system(config: Optional[Dict[str, Any]] = None) -> SystemManager:
    """Initialise global variables and create the system manager.

    Args:
        config: Optional parameter overrides.

    Returns:
        The initialised ``SystemManager``.
    """
    globalvar._init()
    system = SystemManager(config)
    globalvar.set_value("system", system)
    return system
