"""System management: funds, rider recruitment, dispatch and state persistence."""

import json
import logging
import os
from typing import Any, Dict, List, Tuple

from config import (
    CELL_SIZE,
    GRID_SIZE,
    INITIAL_FUNDS,
    MAP_SIZE,
    RIDER_COST,
    RIDER_MIN_FUNDS,
    RIDER_SPAWN_X,
    RIDER_SPAWN_Y,
    RIDER_SPEED,
    STATE_IDLE,
    STATE_PICKING_UP,
)
from globalvar import _init, get_value, set_value
from order import OrderManager
from order_model import Order
from rider import Rider

logger = logging.getLogger(__name__)


class SystemManager:
    """Core coordinator for funds, riders, orders and the simulation clock."""

    def __init__(self) -> None:
        """Create the manager bound to the global state."""
        self.order_manager = OrderManager()

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    @property
    def funds(self) -> int:
        """Current system funds."""
        return int(get_value("funds", 0))

    @property
    def riders(self) -> List[Rider]:
        """The live rider list."""
        return get_value("riders")

    @property
    def running(self) -> bool:
        """Main loop control flag."""
        return bool(get_value("running", False))

    @property
    def time(self) -> int:
        """Current simulated tick."""
        return int(get_value("time", 0))

    def stop(self) -> None:
        """Request the main loop to terminate."""
        set_value("running", False)

    # ------------------------------------------------------------------
    # Rider management
    # ------------------------------------------------------------------
    def idle_riders(self) -> List[Rider]:
        """Return riders in the idle state."""
        return [rider for rider in self.riders if rider.state == STATE_IDLE]

    def create_rider(self) -> Rider:
        """Create and register a new rider with the next unique id.

        Returns:
            The newly created rider.
        """
        rider_id = int(get_value("rider_id_counter", 0)) + 1
        set_value("rider_id_counter", rider_id)
        rider = Rider(rider_id)
        self.riders.append(rider)
        logger.info("Rider %s recruited", rider_id)
        return rider

    def recruit_if_needed(self) -> List[Rider]:
        """Recruit riders while funds allow and pending orders exceed idle riders.

        Each recruit costs ``RIDER_COST`` from system funds.

        Returns:
            The riders recruited during this call.
        """
        new_riders: List[Rider] = []
        while (self.funds >= RIDER_MIN_FUNDS
               and len(self.order_manager.pending) > len(self.idle_riders())):
            set_value("funds", self.funds - RIDER_COST)
            new_riders.append(self.create_rider())
        return new_riders

    def dispatch(self) -> Tuple[List[Rider], List[Order]]:
        """Recruit if necessary and assign pending orders.

        Returns:
            Tuple ``(new_riders, assigned_orders)``.
        """
        new_riders = self.recruit_if_needed()
        assigned = self.order_manager.assign_pending_orders()
        return new_riders, assigned

    # ------------------------------------------------------------------
    # Simulation clock
    # ------------------------------------------------------------------
    def tick(self) -> Dict[str, Any]:
        """Advance the simulation by one unit of time.

        Every rider moves once, pending orders are dispatched and the state
        is checked for consistency. Exceptions are caught per rider so that a
        single failure does not stop the simulation.

        Returns:
            Summary dictionary with keys ``time``, ``events``, ``new_riders``,
            ``assigned``, ``errors`` and ``fixes``.
        """
        set_value("time", self.time + 1)
        events: List[Tuple[int, Dict[str, Any]]] = []
        errors: List[str] = []

        for rider in list(self.riders):
            before = len(rider.log)
            try:
                rider.move()
            except Exception as exc:  # error recovery
                logger.exception("Rider %s failed during tick", rider.rider_id)
                errors.append(f"rider #{rider.rider_id}: {exc}")
            for entry in rider.log[before:]:
                events.append((rider.rider_id, entry))

        new_riders: List[Rider] = []
        assigned: List[Order] = []
        try:
            new_riders, assigned = self.dispatch()
        except Exception as exc:  # error recovery
            logger.exception("Dispatch failed during tick")
            errors.append(f"dispatch: {exc}")

        fixes = self.check_consistency()
        return {
            "time": self.time,
            "events": events,
            "new_riders": new_riders,
            "assigned": assigned,
            "errors": errors,
            "fixes": fixes,
        }

    def check_consistency(self) -> List[str]:
        """Repair inconsistent rider states.

        Returns:
            Human readable descriptions of repaired problems.
        """
        fixes: List[str] = []
        for rider in self.riders:
            if rider.orders and rider.state == STATE_IDLE:
                rider.state = STATE_PICKING_UP
                fixes.append(f"rider #{rider.rider_id} had orders but was idle")
            elif not rider.orders and rider.state != STATE_IDLE:
                rider.state = STATE_IDLE
                rider.special_case = False
                fixes.append(f"rider #{rider.rider_id} had no orders but was busy")
        return fixes

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """Return the full system state as a JSON-serialisable dictionary."""
        return {
            "system_parameters": {
                "initial_funds": INITIAL_FUNDS,
                "rider_cost": RIDER_COST,
                "rider_min_funds": RIDER_MIN_FUNDS,
                "rider_spawn": [RIDER_SPAWN_X, RIDER_SPAWN_Y],
                "rider_speed": RIDER_SPEED,
                "map_size": MAP_SIZE,
                "cell_size": CELL_SIZE,
                "grid_size": GRID_SIZE,
            },
            "funds": self.funds,
            "time": self.time,
            "rider_id_counter": int(get_value("rider_id_counter", 0)),
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.order_manager.history],
        }

    def save_state(self, path: str) -> str:
        """Write the system state to a JSON file.

        Args:
            path: Destination file path.

        Returns:
            The absolute path of the written file.

        Raises:
            OSError: If the file cannot be written.
        """
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.snapshot(), handle, indent=2)
        return os.path.abspath(path)


def init_system() -> SystemManager:
    """Initialise global state and return the system manager.

    Sets funds to 1000, an empty rider list, rider id counter to 0, the
    running flag to True, and the simulated clock to 0.

    Returns:
        A ready-to-use SystemManager.
    """
    _init()
    set_value("funds", INITIAL_FUNDS)
    set_value("riders", [])
    set_value("rider_id_counter", 0)
    set_value("running", True)
    set_value("time", 0)
    set_value("pending_orders", [])
    set_value("orders", [])
    logger.info("System initialised with funds=%s", INITIAL_FUNDS)
    return SystemManager()
