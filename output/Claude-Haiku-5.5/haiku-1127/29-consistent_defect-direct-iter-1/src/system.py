"""System-level state management: funds, riders, recruitment and the tick loop."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import globalvar
from rider import Rider

logger = logging.getLogger(__name__)

RECRUIT_MIN_FUNDS = 300
RECRUIT_COST = 500
INITIAL_FUNDS = 1000


class SystemManager:
    """Manages system funds, the rider list and simulated time.

    All state lives in the ``globalvar`` store under the keys "funds",
    "riders", "rider_id_counter", "running" and "tick".
    """

    def __init__(self) -> None:
        """Ensure the rider list exists in the global store."""
        if globalvar.get_value("riders") is None:
            globalvar.set_value("riders", [])

    # ------------------------------------------------------------------
    # Funds and riders
    # ------------------------------------------------------------------
    @property
    def funds(self) -> int:
        """Current system fund balance (may be negative)."""
        return int(globalvar.get_value("funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        globalvar.set_value("funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """The dynamic list of riders."""
        return globalvar.get_value("riders")

    def add_funds(self, amount: int) -> int:
        """Add an amount to system funds and return the new balance."""
        self.funds = self.funds + int(amount)
        return self.funds

    def find_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with the given ID, or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def remove_rider(self, rider_id: int) -> bool:
        """Remove a rider from the list.

        Returns:
            True if a rider was removed.
        """
        rider = self.find_rider(rider_id)
        if rider is None:
            return False
        self.riders.remove(rider)
        return True

    def idle_riders(self) -> List[Rider]:
        """Return riders whose state is idle."""
        return [r for r in self.riders if r.is_idle()]

    def create_rider(self) -> Rider:
        """Recruit a new rider at (400, 400), deducting the recruitment cost.

        Returns:
            The newly created Rider.
        """
        counter = int(globalvar.get_value("rider_id_counter", 0) or 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        self.funds = self.funds - RECRUIT_COST
        logger.info("Recruited rider %s; funds now %s", counter, self.funds)
        return rider

    def maybe_recruit(self, pending_count: int) -> Optional[Rider]:
        """Recruit a rider if funds allow and pending orders exceed idle riders.

        Args:
            pending_count: Number of orders waiting for a rider.

        Returns:
            The new Rider, or None if no recruitment happened.
        """
        if self.funds >= RECRUIT_MIN_FUNDS and pending_count > len(self.idle_riders()):
            return self.create_rider()
        return None

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def tick(self) -> int:
        """Advance the simulation by one tick.

        Every rider moves once, then the global tick counter is incremented.

        Returns:
            The new tick value.
        """
        for rider in list(self.riders):
            rider.move()
        new_tick = globalvar.current_tick() + 1
        globalvar.set_value("tick", new_tick)
        return new_tick

    def is_running(self) -> bool:
        """Return the main-loop running flag."""
        return bool(globalvar.get_value("running", False))

    def stop(self) -> None:
        """Clear the running flag so the main loop exits."""
        globalvar.set_value("running", False)

    def check_consistency(self) -> List[str]:
        """Check internal state consistency and return a list of problems.

        Returns:
            List of human-readable issue descriptions (empty if consistent).
        """
        issues: List[str] = []
        if not isinstance(self.funds, int):
            issues.append("System funds are not an integer.")
        ids = [r.rider_id for r in self.riders]
        if len(set(ids)) != len(ids):
            issues.append("Duplicate rider IDs detected.")
        for rider in self.riders:
            active = rider.active_orders()
            if active and rider.state == 0:
                issues.append(f"Rider #{rider.rider_id} has active orders but is idle.")
            if not active and rider.state != 0:
                issues.append(f"Rider #{rider.rider_id} has no orders but state={rider.state}.")
            for order in active:
                if order.rider_id != rider.rider_id:
                    issues.append(
                        f"Order #{order.id} is listed for rider #{rider.rider_id} "
                        f"but assigned to rider #{order.rider_id}."
                    )
        return issues

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the system state."""
        orders = globalvar.get_value("orders") or []
        return {
            "tick": globalvar.current_tick(),
            "funds": self.funds,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "parameters": {
                "initial_funds": INITIAL_FUNDS,
                "recruit_min_funds": RECRUIT_MIN_FUNDS,
                "recruit_cost": RECRUIT_COST,
                "map_size": 800,
                "cell_size": 100,
            },
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in orders],
        }

    def save_state(self, path: str) -> str:
        """Write the system snapshot to a JSON file.

        Args:
            path: Destination file path.

        Returns:
            The path that was written.
        """
        data = self.snapshot()
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp_path, path)
        logger.info("State saved to %s", path)
        return path


def init_system() -> SystemManager:
    """Initialise global variables and return a SystemManager.

    Sets funds to 1000, an empty rider list, rider ID counter to 0, the
    running flag to True and the tick to 0.

    Returns:
        A ready-to-use SystemManager.
    """
    globalvar._init()
    globalvar.set_value("funds", INITIAL_FUNDS)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    return SystemManager()
