"""System initialization, funds, rider recruitment and simulation clock."""

import json
import logging
from typing import Any, Dict, List, Optional

import globalvar
from rider import Rider

logger = logging.getLogger(__name__)

INITIAL_FUNDS = 1000
RECRUIT_MIN_FUNDS = 300
RECRUIT_COST = 500


def init_system() -> None:
    """Initialize all core parameters and reset the global store.

    Sets funds to 1000, an empty rider list, rider id counter 0, the running
    flag to True, the simulated time to 0 and an empty order list.
    """
    globalvar._init()
    globalvar.set_value("funds", INITIAL_FUNDS)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("is_running", True)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)
    globalvar.set_value("time", 0)
    logger.info("System initialized with funds=%d", INITIAL_FUNDS)


class SystemManager:
    """Facade over the global store for funds, riders and the simulation clock.

    The class is stateless; every property reads and writes the global store,
    so multiple instances always see the same system state.
    """

    @property
    def funds(self) -> int:
        """Current system funds (may be negative)."""
        return int(globalvar.get_value("funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        """Set the system funds.

        Args:
            value: New fund balance.
        """
        globalvar.set_value("funds", int(value))

    @property
    def rider_id_counter(self) -> int:
        """Last rider id that was assigned."""
        return int(globalvar.get_value("rider_id_counter", 0))

    @property
    def is_running(self) -> bool:
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("is_running", True))

    @property
    def time(self) -> int:
        """Current simulation tick."""
        return int(globalvar.get_value("time", 0))

    @property
    def riders(self) -> List[Rider]:
        """Live list of riders."""
        return globalvar.get_value("riders", [])

    @property
    def orders(self) -> List[Any]:
        """Live list of orders."""
        return globalvar.get_value("orders", [])

    def stop(self) -> None:
        """Request the main loop to exit."""
        globalvar.set_value("is_running", False)

    def get_rider(self, rider_id: int) -> Optional[Rider]:
        """Look up a rider by id.

        Args:
            rider_id: Identifier to search for.

        Returns:
            The matching Rider, or None.
        """
        return next((r for r in self.riders if r.rider_id == rider_id), None)

    def idle_rider_count(self) -> int:
        """Count riders that are currently available for new orders.

        Returns:
            Number of idle riders.
        """
        return sum(1 for r in self.riders if r.is_idle())

    def recruit_rider(self) -> Rider:
        """Create a new rider, deducting the recruitment cost.

        Returns:
            The newly created Rider.
        """
        self.funds = self.funds - RECRUIT_COST
        new_id = self.rider_id_counter + 1
        globalvar.set_value("rider_id_counter", new_id)
        rider = Rider(new_id)
        self.riders.append(rider)
        logger.info("Recruited rider %d; funds now %d", new_id, self.funds)
        return rider

    def recruit_if_needed(self, pending_count: int, idle_count: int) -> List[Rider]:
        """Recruit riders while funds allow and pending orders exceed idle riders.

        Args:
            pending_count: Number of orders waiting for a rider.
            idle_count: Number of currently idle riders.

        Returns:
            List of riders created by this call (possibly empty).
        """
        new_riders: List[Rider] = []
        idle = idle_count
        while self.funds >= RECRUIT_MIN_FUNDS and pending_count > idle:
            new_riders.append(self.recruit_rider())
            idle += 1
        return new_riders

    def tick(self) -> int:
        """Advance the simulation by one tick and move every rider.

        Errors raised by an individual rider are logged and do not stop the
        remaining riders, providing automatic recovery.

        Returns:
            The new simulation time.
        """
        globalvar.set_value("time", self.time + 1)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # noqa: BLE001 - keep simulation running
                logger.exception("Error while moving rider %d", rider.rider_id)
        return self.time

    def snapshot(self) -> Dict[str, Any]:
        """Build a JSON-compatible snapshot of the whole system.

        Returns:
            Dictionary with system parameters, riders and order history.
        """
        return {
            "funds": self.funds,
            "rider_id_counter": self.rider_id_counter,
            "time": self.time,
            "is_running": self.is_running,
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.orders],
        }

    def save_state(self, path: str) -> None:
        """Persist the system snapshot to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.snapshot(), handle, indent=2)
        logger.info("State saved to %s", path)
