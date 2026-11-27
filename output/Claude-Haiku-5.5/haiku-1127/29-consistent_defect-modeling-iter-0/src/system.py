"""System-level state management and simulation clock.

The :class:`SystemManager` owns the funds, rider list, ID counter, running
flag and simulated time. All values are kept in :mod:`globalvar`.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import globalvar
from config import (GRID_DIMENSION, CELL_SIZE, INITIAL_FUNDS, MAP_SIZE,
                    RECRUIT_COST, RECRUIT_MIN_FUNDS)
from rider import Rider

logger = logging.getLogger(__name__)


def init_system() -> None:
    """Initialise all core global parameters for a fresh simulation."""
    globalvar._init()
    globalvar.set_value("funds", INITIAL_FUNDS)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("simulated_time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("grid", {
        "map_size": MAP_SIZE,
        "cell_size": CELL_SIZE,
        "grid_dimension": GRID_DIMENSION,
    })
    logger.info("System initialised with funds=%s", INITIAL_FUNDS)


class SystemManager:
    """Core coordinator for funds, riders, clock and running state."""

    def __init__(self) -> None:
        """Wrap the global state, initialising it if necessary."""
        if globalvar.get_value("riders") is None:
            init_system()

    # ------------------------------------------------------------------
    # Global state accessors
    # ------------------------------------------------------------------
    @property
    def funds(self) -> int:
        """Current system funds (may be negative)."""
        return globalvar.get_value("funds", 0)

    @funds.setter
    def funds(self, value: int) -> None:
        globalvar.set_value("funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """The dynamic list of riders."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def running(self) -> bool:
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("running", False))

    @running.setter
    def running(self, value: bool) -> None:
        globalvar.set_value("running", bool(value))

    @property
    def simulated_time(self) -> int:
        """Current simulated tick."""
        return globalvar.get_value("simulated_time", 0)

    # ------------------------------------------------------------------
    # Rider management
    # ------------------------------------------------------------------
    def create_rider(self) -> Rider:
        """Create a new rider with an auto-incremented ID and add it to the list."""
        counter = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        logger.info("Rider %s recruited", counter)
        return rider

    def get_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with ``rider_id`` or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def idle_rider_count(self) -> int:
        """Number of riders that are idle with no active orders."""
        return sum(1 for r in self.riders if r.is_idle)

    def recruit_if_needed(self, pending_order_count: int) -> Optional[Rider]:
        """Recruit a rider when funds allow and pending orders exceed idle riders.

        Args:
            pending_order_count: Number of orders waiting for a rider.

        Returns:
            The newly created rider, or None if no recruitment occurred.
        """
        if self.funds >= RECRUIT_MIN_FUNDS and \
                pending_order_count > self.idle_rider_count():
            self.funds = self.funds - RECRUIT_COST
            return self.create_rider()
        return None

    # ------------------------------------------------------------------
    # Simulation clock
    # ------------------------------------------------------------------
    def tick(self) -> None:
        """Advance simulated time by one unit and move every rider.

        Exceptions raised by an individual rider are logged and that rider's
        state is repaired so the rest of the simulation keeps running.
        """
        globalvar.set_value("simulated_time", self.simulated_time + 1)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive recovery
                logger.exception("Error moving rider %s", rider.rider_id)
                rider.repair_state()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the whole system."""
        return {
            "funds": self.funds,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "simulated_time": self.simulated_time,
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in (globalvar.get_value("orders") or [])],
        }

    def save_state(self, path: str) -> None:
        """Write the system snapshot to a JSON file at ``path``."""
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
        logger.info("State saved to %s", path)
