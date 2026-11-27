"""System manager: funds, rider recruitment, simulation ticks and persistence."""

import json
import logging
from typing import Any, Dict, List

import globalvar
from rider import Rider

logger = logging.getLogger(__name__)

CONFIG: Dict[str, int] = {
    "initial_funds": 1000,
    "recruit_min_funds": 300,
    "recruit_cost": 500,
    "rider_start_x": 400,
    "rider_start_y": 400,
    "rider_speed": 20,
}


def load_config(path: str) -> None:
    """Override system parameters from a JSON file.

    Only keys already present in ``CONFIG`` are applied. Unknown keys are ignored.

    Args:
        path: Path to a JSON file such as ``{"initial_funds": 2000}``.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the file is not valid JSON or a value is not an integer.
    """
    with open(path, "r") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Configuration file must contain a JSON object")
    for key in CONFIG:
        if key in data:
            CONFIG[key] = int(data[key])
    logger.info("Configuration loaded from %s", path)


def init_system() -> "SystemManager":
    """Initialise global state and return the system manager.

    Sets funds to the configured initial value, an empty rider list, rider ID
    counter 0, running state True, tick 0 and an empty order history.

    Returns:
        A ready-to-use ``SystemManager``.
    """
    globalvar._init()
    globalvar.set_value("system_funds", CONFIG["initial_funds"])
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    logger.info("System initialised with funds=%s", CONFIG["initial_funds"])
    return SystemManager()


class SystemManager:
    """Manages system funds, rider resources, the tick loop and persistence."""

    @property
    def funds(self) -> int:
        """Current system funds (may be negative)."""
        return int(globalvar.get_value("system_funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        globalvar.set_value("system_funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """The dynamic rider list."""
        return globalvar.get_value("riders", [])

    @property
    def running(self) -> bool:
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("running", False))

    def stop(self) -> None:
        """Request the main loop to terminate."""
        globalvar.set_value("running", False)
        logger.info("System stop requested")

    @property
    def tick(self) -> int:
        """Current simulated time."""
        return int(globalvar.get_value("tick", 0))

    def idle_rider_count(self) -> int:
        """Return the number of riders with no active orders."""
        return sum(1 for rider in self.riders if not rider.active_orders())

    def can_recruit(self) -> bool:
        """Return True if funds meet the recruitment threshold."""
        return self.funds >= CONFIG["recruit_min_funds"]

    def recruit_rider(self) -> Rider:
        """Create a new rider, deduct the recruitment cost and register it.

        Returns:
            The newly created rider.

        Raises:
            RuntimeError: If funds are below the recruitment threshold.
        """
        if not self.can_recruit():
            raise RuntimeError("Insufficient funds to recruit a rider")
        new_id = int(globalvar.get_value("rider_id_counter", 0)) + 1
        globalvar.set_value("rider_id_counter", new_id)
        self.funds = self.funds - CONFIG["recruit_cost"]
        rider = Rider(new_id, CONFIG["rider_start_x"], CONFIG["rider_start_y"],
                      CONFIG["rider_speed"])
        self.riders.append(rider)
        logger.info("Recruited rider %s; funds now %s", new_id, self.funds)
        return rider

    def advance_tick(self, steps: int = 1) -> None:
        """Advance the simulation by ``steps`` ticks.

        Each tick increments the clock and calls ``move()`` on every rider. A
        rider that raises an exception is recovered and the loop continues.

        Args:
            steps: Number of ticks to simulate.
        """
        for _ in range(steps):
            globalvar.set_value("tick", self.tick + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception:  # pylint: disable=broad-except
                    logger.exception("Rider %s failed; recovering", rider.rider_id)
                    rider.recover()

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of system state."""
        return {
            "system_funds": self.funds,
            "rider_id_counter": int(globalvar.get_value("rider_id_counter", 0)),
            "tick": self.tick,
            "config": dict(CONFIG),
            "riders": [
                {
                    "rider_id": r.rider_id,
                    "x": r.x,
                    "y": r.y,
                    "speed": r.speed,
                    "state": r.state,
                    "special_case": r.special_case,
                    "order_ids": [o.id for o in r.orders],
                }
                for r in self.riders
            ],
            "orders": [o.to_dict() for o in globalvar.get_value("orders", [])],
        }

    def save_state(self, path: str) -> None:
        """Write the system parameters, riders and order history to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        with open(path, "w") as handle:
            json.dump(self.to_dict(), handle, indent=2)
        logger.info("State saved to %s", path)
