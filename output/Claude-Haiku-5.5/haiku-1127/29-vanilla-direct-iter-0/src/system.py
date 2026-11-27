"""System-level management: funds, riders, ticks, recruitment and persistence."""

import json
import logging
import os

import globalvar
from globalvar import get_value, set_value
from rider import IDLE, Rider

logger = logging.getLogger("dispatch.system")


def init_system() -> None:
    """Initialise all global variables to their startup defaults."""
    globalvar._init()
    logger.info("System initialised")


class SystemManager:
    """Manages funds, the rider roster, the simulated clock and recruitment."""

    @property
    def is_running(self) -> bool:
        """True while the main loop should keep running."""
        return bool(get_value("system_running", False))

    def stop(self) -> None:
        """Signal the main loop to terminate."""
        set_value("system_running", False)

    @property
    def funds(self) -> int:
        """Current system fund balance."""
        return int(get_value("system_funds", 0))

    def riders(self) -> list:
        """Return the rider list."""
        return get_value("riders", [])

    def idle_rider_count(self) -> int:
        """Return the number of riders free to accept new orders."""
        return sum(1 for r in self.riders() if r.is_idle())

    def create_rider(self) -> Rider:
        """Create a new rider with an auto-incremented ID and add it to the list.

        Returns:
            The newly created Rider.
        """
        counter = int(get_value("rider_id_counter", 0)) + 1
        set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders().append(rider)
        logger.info("Recruited rider %s", counter)
        return rider

    def recruit_if_needed(self, pending_count: int) -> list:
        """Recruit riders while funds allow and pending orders exceed idle riders.

        Each recruit costs ``recruit_cost`` from system funds.

        Args:
            pending_count: Number of orders waiting for a rider.

        Returns:
            List of newly created Rider objects (possibly empty).
        """
        created = []
        cost = int(get_value("recruit_cost", 300))
        while self.funds >= cost and pending_count > self.idle_rider_count():
            set_value("system_funds", self.funds - cost)
            created.append(self.create_rider())
        return created

    def tick(self) -> None:
        """Advance the simulation by one unit of time."""
        set_value("tick", int(get_value("tick", 0)) + 1)
        for rider in list(self.riders()):
            try:
                rider.move()
            except Exception:  # error recovery: keep the simulation alive
                logger.exception("Rider %s failed; recovering", rider.rider_id)
                rider.reset_movement()
                rider.state = IDLE if not rider.orders else rider.state
        for issue in self.check_consistency():
            logger.warning(issue)

    def check_consistency(self) -> list:
        """Check rider/order state consistency and repair simple faults.

        Returns:
            List of human readable descriptions of issues found.
        """
        issues = []
        for rider in self.riders():
            if rider.state not in (0, 1, 2):
                issues.append(f"Rider {rider.rider_id} has invalid state "
                              f"{rider.state}; reset to idle")
                rider.state = IDLE
                rider.reset_movement()
            if rider.state != IDLE and not rider.orders:
                issues.append(f"Rider {rider.rider_id} active without orders; "
                              "reset to idle")
                rider.state = IDLE
                rider.reset_movement()
            for order in list(rider.orders):
                if order.status == "completed":
                    issues.append(f"Completed order {order.id} still on "
                                  f"rider {rider.rider_id}; removed")
                    rider.orders.remove(order)
        return issues


def save_snapshot(path: str) -> str:
    """Write the current system state to a JSON file.

    Args:
        path: Destination file path.

    Returns:
        The path written.
    """
    data = {
        "system_funds": get_value("system_funds"),
        "tick": get_value("tick"),
        "rider_id_counter": get_value("rider_id_counter"),
        "riders": [{
            "rider_id": r.rider_id,
            "x": r.x,
            "y": r.y,
            "speed": r.speed,
            "state": r.state,
            "orders": [o.id for o in r.orders],
            "special_case": r.special_case,
        } for r in get_value("riders", [])],
        "orders": [o.to_dict() for o in get_value("orders", [])],
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    logger.info("Snapshot saved to %s", path)
    return path


def load_config(path: str) -> dict:
    """Load system parameters from a JSON configuration file.

    Recognised keys: "initial_funds", "recruit_cost", "rider_speed".
    Missing files are ignored and default values are kept.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        The parsed configuration dictionary (empty if none was loaded).
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Could not read config %s: %s", path, exc)
        return {}
    if "initial_funds" in config:
        set_value("system_funds", int(config["initial_funds"]))
    if "recruit_cost" in config:
        set_value("recruit_cost", int(config["recruit_cost"]))
    if "rider_speed" in config:
        set_value("rider_speed", int(config["rider_speed"]))
    return config
