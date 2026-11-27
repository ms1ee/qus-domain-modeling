"""System-level management: initialization, funds, recruitment, clock and persistence."""

import json
import logging
from typing import Any, Dict, List, Optional

import globalvar
from rider import STATE_IDLE, STATE_PICKING_UP, Rider

LOGGER = logging.getLogger(__name__)

CONFIG_KEYS = (
    "order_fee",
    "recruit_threshold",
    "recruit_cost",
    "rider_speed",
    "max_ticks",
)


def init_system() -> None:
    """Initialize (or reset) all global system parameters to defaults."""
    globalvar._init()
    LOGGER.info("system initialized")


def load_config(path: str) -> Dict[str, int]:
    """Load system parameters from a JSON configuration file.

    Args:
        path: Path to the JSON file.

    Returns:
        Dictionary of parameters that were applied.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON is malformed or a parameter is invalid.
    """
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("configuration root must be a JSON object")

    applied: Dict[str, int] = {}
    for key in CONFIG_KEYS:
        if key not in data:
            continue
        value = data[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"config '{key}' must be an integer")
        if key in ("rider_speed", "max_ticks", "recruit_threshold") and value <= 0:
            raise ValueError(f"config '{key}' must be positive")
        globalvar.set_value(key, value)
        applied[key] = value
    LOGGER.info("loaded configuration from %s: %s", path, applied)
    return applied


class SystemManager:
    """Manages system funds, rider recruitment, the simulated clock and persistence.

    All state lives in the global store (see ``globalvar``).
    """

    @property
    def funds(self) -> int:
        """Current system fund balance (may be negative)."""
        return int(globalvar.get_value("funds", 0))

    @property
    def riders(self) -> List[Rider]:
        """The live rider list."""
        return globalvar.get_value("riders", [])

    @property
    def running(self) -> bool:
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("running_state", True))

    def add_funds(self, amount: int) -> int:
        """Add ``amount`` to the fund balance.

        Args:
            amount: Signed amount to add.

        Returns:
            The new fund balance.
        """
        new_value = self.funds + int(amount)
        globalvar.set_value("funds", new_value)
        return new_value

    def find_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with ``rider_id`` or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def recruit_rider(self) -> Rider:
        """Create a new idle rider with an auto-incremented ID.

        The recruitment cost is deducted from the funds.

        Returns:
            The newly created Rider.
        """
        counter = int(globalvar.get_value("rider_id_counter", 0)) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        self.add_funds(-int(globalvar.get_value("recruit_cost", 300)))
        LOGGER.info("recruited rider %s (state=%s)", counter, STATE_IDLE)
        return rider

    def check_recruitment(self) -> Optional[Rider]:
        """Recruit a rider automatically when funds reach the threshold.

        Returns:
            The new Rider if one was created, otherwise None.
        """
        threshold = int(globalvar.get_value("recruit_threshold", 300))
        if self.funds >= threshold:
            return self.recruit_rider()
        return None

    def tick(self) -> Optional[Rider]:
        """Advance the simulation by one tick.

        Increments the simulated clock, moves every rider and checks the
        recruitment trigger. A failing rider is recovered rather than
        crashing the whole simulation.

        Returns:
            A newly recruited Rider, or None.
        """
        globalvar.set_value(
            "simulated_time", int(globalvar.get_value("simulated_time", 0)) + 1
        )
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("rider %s failed during move; recovering", rider.rider_id)
                self._recover_rider(rider)
        return self.check_recruitment()

    @staticmethod
    def _recover_rider(rider: Rider) -> None:
        """Reset a rider's transient movement state after an exception.

        Args:
            rider: The rider to repair. Orders are preserved.
        """
        rider.path = []
        rider.special_case = False
        rider.state = STATE_PICKING_UP if rider.orders else STATE_IDLE

    def stop(self) -> None:
        """Signal the main loop to terminate."""
        globalvar.set_value("running_state", False)

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serializable snapshot of the whole system."""
        return {
            "funds": self.funds,
            "simulated_time": int(globalvar.get_value("simulated_time", 0)),
            "rider_id_counter": int(globalvar.get_value("rider_id_counter", 0)),
            "config": {key: globalvar.get_value(key) for key in CONFIG_KEYS},
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in globalvar.get_value("orders", [])],
        }

    def save_state(self, path: str) -> None:
        """Persist the system state to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.snapshot(), handle, indent=2)
        LOGGER.info("state saved to %s", path)
