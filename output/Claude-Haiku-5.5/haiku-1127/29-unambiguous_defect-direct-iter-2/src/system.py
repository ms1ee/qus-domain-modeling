"""System-level state management: funds, rider recruitment, ticks and persistence."""

import json
import logging
from typing import Any, Dict, List, Optional

import globalvar
from path_planner import PathPlanner
from rider import STATE_IDLE, Rider
from order_model import STATUS_COMPLETED

logger = logging.getLogger(__name__)

DEFAULT_PARAMS: Dict[str, int] = {
    "initial_funds": 10000,
    "rider_cost": 500,
    "max_riders": 20,
    "rider_speed": 100,
    "load_penalty": 100,
    "running_cost": 1,
}
CONFIG_FILE = "config.json"
DEFAULT_STATE_FILE = "dispatch_state.json"


def init_system() -> "SystemManager":
    """Initialise global state and return a :class:`SystemManager`.

    Sets the starting funds, an empty rider list, a zeroed rider ID counter,
    the running flag, the tick counter and default parameters.
    """
    globalvar._init()
    globalvar.set_value("params", dict(DEFAULT_PARAMS))
    globalvar.set_value("funds", DEFAULT_PARAMS["initial_funds"])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("riders", [])
    globalvar.set_value("orders", [])
    logger.info("System initialised with funds=%d", DEFAULT_PARAMS["initial_funds"])
    return SystemManager()


def load_config(path: str = CONFIG_FILE) -> bool:
    """Load system parameters from a JSON configuration file.

    The file may contain a ``"params"`` object whose keys override entries of
    :data:`DEFAULT_PARAMS`. Unknown or invalid entries are ignored with a
    warning.

    Returns:
        True if the file was read and applied, False otherwise.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        logger.warning("Could not load configuration %s: %s", path, exc)
        return False

    params = dict(globalvar.get_value("params", DEFAULT_PARAMS) or DEFAULT_PARAMS)
    for key, value in (data.get("params") or {}).items():
        valid = isinstance(value, int) and not isinstance(value, bool)
        if key in DEFAULT_PARAMS and valid and value >= 0:
            if key == "rider_speed" and value <= 0:
                logger.warning("Ignoring non-positive rider_speed")
                continue
            params[key] = value
        else:
            logger.warning("Ignoring invalid configuration entry %r", key)
    globalvar.set_value("params", params)

    if not globalvar.get_value("riders") and int(globalvar.get_value("tick", 0) or 0) == 0:
        globalvar.set_value("funds", params["initial_funds"])
    logger.info("Configuration loaded from %s", path)
    return True


class SystemManager:
    """Manages funds, riders, the simulation clock and system state."""

    @staticmethod
    def _params() -> Dict[str, int]:
        """Return the active parameter dictionary."""
        return globalvar.get_value("params", DEFAULT_PARAMS) or DEFAULT_PARAMS

    @property
    def funds(self) -> int:
        """Current system fund balance (may be negative)."""
        return int(globalvar.get_value("funds", 0) or 0)

    def _set_funds(self, value: int) -> None:
        """Store a new fund balance."""
        globalvar.set_value("funds", int(value))

    def add_funds(self, amount: int) -> None:
        """Add ``amount`` (may be negative) to the fund balance."""
        self._set_funds(self.funds + int(amount))

    @property
    def riders(self) -> List[Rider]:
        """The live rider list."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def tick_count(self) -> int:
        """Number of simulated ticks elapsed."""
        return int(globalvar.get_value("tick", 0) or 0)

    @property
    def is_running(self) -> bool:
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("running", False))

    def stop(self) -> None:
        """Request the main loop to terminate."""
        globalvar.set_value("running", False)
        logger.info("System stop requested")

    def idle_riders(self) -> List[Rider]:
        """Return riders in the idle state with no queued orders."""
        return [r for r in self.riders if r.state == STATE_IDLE and not r.orders]

    def can_recruit(self) -> bool:
        """Return True if funds and the rider limit allow a new recruit."""
        params = self._params()
        return len(self.riders) < params["max_riders"] and self.funds >= params["rider_cost"]

    def recruit_rider(self) -> Optional[Rider]:
        """Recruit a new rider, deducting the recruitment cost.

        Returns:
            The new :class:`Rider`, or None if recruitment is not possible.
        """
        if not self.can_recruit():
            logger.info("Recruitment skipped (funds=%d, riders=%d)", self.funds, len(self.riders))
            return None
        params = self._params()
        self._set_funds(self.funds - params["rider_cost"])
        rider_id = int(globalvar.get_value("rider_id_counter", 0) or 0) + 1
        globalvar.set_value("rider_id_counter", rider_id)
        rider = Rider(rider_id, speed=params["rider_speed"])
        self.riders.append(rider)
        logger.info("Recruited rider %d (funds now %d)", rider_id, self.funds)
        return rider

    def tick(self) -> int:
        """Advance the simulation by one tick.

        Moves every rider, charges running costs and runs consistency checks.
        Exceptions raised by an individual rider are logged and recovered so
        that one faulty rider cannot stop the simulation.

        Returns:
            The new tick count.
        """
        if not self.is_running:
            return self.tick_count
        globalvar.set_value("tick", self.tick_count + 1)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # noqa: BLE001 - recovery boundary
                logger.exception("Error while moving rider %d", rider.rider_id)
                rider.recover()
        cost = self._params()["running_cost"] * len(self.riders)
        if cost:
            self._set_funds(self.funds - cost)
        self.check_consistency()
        return self.tick_count

    def check_consistency(self) -> List[str]:
        """Detect and repair inconsistent rider states.

        Returns:
            Human readable descriptions of the issues found and repaired.
        """
        issues: List[str] = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)

            if rider.state not in (0, 1, 2):
                issues.append(f"rider {rider.rider_id} has invalid state {rider.state}")
                rider.recover()
            elif rider.state != STATE_IDLE and not rider.orders:
                issues.append(f"rider {rider.rider_id} active without orders")
                rider.recover()

            finished = [o for o in rider.orders if o.status == STATUS_COMPLETED]
            if finished:
                issues.append(f"rider {rider.rider_id} still holds completed orders")
                rider.orders = [o for o in rider.orders if o.status != STATUS_COMPLETED]

            if not PathPlanner.is_on_road(rider.x, rider.y):
                issues.append(f"rider {rider.rider_id} off road at ({rider.x}, {rider.y})")
                rider.x = PathPlanner.snap_to_road(rider.x)
                rider.y = PathPlanner.snap_to_road(rider.y)
                rider.recover()

        for issue in issues:
            logger.warning("Consistency check: %s", issue)
        return issues

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the full system state."""
        return {
            "params": dict(self._params()),
            "funds": self.funds,
            "tick": self.tick_count,
            "rider_id_counter": int(globalvar.get_value("rider_id_counter", 0) or 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in (globalvar.get_value("orders", []) or [])],
        }

    def save_state(self, path: str = DEFAULT_STATE_FILE) -> bool:
        """Persist the system state (parameters, riders, orders) as JSON.

        Returns:
            True on success, False if the file could not be written.
        """
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self.snapshot(), handle, indent=2)
        except OSError as exc:
            logger.error("Failed to save state to %s: %s", path, exc)
            return False
        logger.info("State saved to %s", path)
        return True
