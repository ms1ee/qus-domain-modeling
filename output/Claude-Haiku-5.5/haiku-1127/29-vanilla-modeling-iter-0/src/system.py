"""System initialization, funds management, rider recruitment and clock."""

import logging
from typing import Any, Dict, List, Optional

import globalvar
from rider import Rider, STATE_IDLE

LOGGER = logging.getLogger("dispatch.system")

DEFAULT_CONFIG: Dict[str, int] = {
    "initial_funds": 1000,
    "recruit_cost": 300,
    "recruit_threshold": 300,
}


class SystemManager:
    """Facade over the global state for funds, riders and simulated time.

    The state itself lives in :mod:`globalvar`; this class provides the
    business operations (recruitment, ticking, shutdown).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Create the manager using defaults overridden by ``config``.

        Args:
            config: Optional mapping of known parameter names to integers.
        """
        self.config: Dict[str, int] = dict(DEFAULT_CONFIG)
        if config:
            for key, value in config.items():
                if key in self.config:
                    self.config[key] = int(value)

    @property
    def funds(self) -> int:
        """Current system fund balance (may be negative)."""
        return int(globalvar.get_value("funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        """Set the system fund balance."""
        globalvar.set_value("funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """The dynamic rider list."""
        return globalvar.get_value("riders", [])

    @property
    def simulated_time(self) -> int:
        """Current simulated tick."""
        return int(globalvar.get_value("simulated_time", 0) or 0)

    def is_running(self) -> bool:
        """Return the system running state."""
        return bool(globalvar.get_value("is_running", False))

    def shutdown(self) -> None:
        """Clear the running flag so the main loop exits."""
        globalvar.set_value("is_running", False)
        LOGGER.info("System shutdown requested")

    def idle_riders(self) -> List[Rider]:
        """Return all riders that are idle (no state and no orders)."""
        return [rider for rider in self.riders
                if rider.state == STATE_IDLE and not rider.orders]

    def should_recruit(self) -> bool:
        """Return True when funds allow recruitment and demand exceeds supply.

        Trigger: funds >= recruit_threshold and pending orders > idle riders.
        """
        pending = len(globalvar.get_value("pending_orders", []) or [])
        return (self.funds >= self.config["recruit_threshold"]
                and pending > len(self.idle_riders()))

    def create_rider(self) -> Rider:
        """Recruit a new rider, deducting the recruitment cost.

        Returns:
            The newly created Rider.
        """
        counter = int(globalvar.get_value("rider_id_counter", 0)) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        self.funds = self.funds - self.config["recruit_cost"]
        LOGGER.info("Recruited rider %d; funds now %d", counter, self.funds)
        return rider

    def maybe_recruit(self) -> Optional[Rider]:
        """Recruit a rider if the trigger conditions hold.

        Returns:
            The new Rider, or None if no recruitment happened.
        """
        if self.should_recruit():
            return self.create_rider()
        return None

    def tick(self) -> int:
        """Advance the simulated clock by one tick and move every rider.

        Exceptions raised by a single rider are logged and do not stop the
        other riders (error recovery).

        Returns:
            The new simulated time.
        """
        globalvar.set_value("simulated_time", self.simulated_time + 1)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive recovery
                LOGGER.exception("Rider %d failed during tick",
                                 rider.rider_id)
        return self.simulated_time


_manager: Optional[SystemManager] = None


def init_system(config: Optional[Dict[str, Any]] = None) -> SystemManager:
    """Initialise the global state and the system manager.

    Resets the global store to defaults, applies configuration and sets the
    starting funds (1000 unless configured otherwise).

    Args:
        config: Optional configuration overrides.

    Returns:
        The initialised SystemManager.
    """
    global _manager
    globalvar._init()
    _manager = SystemManager(config)
    globalvar.set_value("funds", _manager.config["initial_funds"])
    LOGGER.info("System initialised with funds %d", _manager.funds)
    return _manager


def get_system() -> SystemManager:
    """Return the active SystemManager, initialising it if necessary."""
    if _manager is None:
        return init_system()
    return _manager
