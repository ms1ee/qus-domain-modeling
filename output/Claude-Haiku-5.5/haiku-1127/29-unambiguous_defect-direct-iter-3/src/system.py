"""System state management: funds, rider pool, simulation clock and persistence."""

import json
import logging
import os

import config
import globalvar
import grid
from order_model import STATUS_COMPLETED
from rider import Rider

logger = logging.getLogger("dispatch.system")


def apply_config_file(path):
    """Load tunable parameters from a JSON configuration file.

    The file may contain the parameters at top level or inside a
    ``"parameters"`` object. Unknown keys are ignored.

    Args:
        path: Path to the JSON file.

    Returns:
        dict: The parameters that were applied.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON is malformed or a value is invalid.
    """
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("configuration file must contain a JSON object")
    params = data.get("parameters", data)
    if not isinstance(params, dict):
        raise ValueError("'parameters' must be a JSON object")

    applied = {}
    for name in config.TUNABLE_PARAMS:
        if name not in params:
            continue
        value = params[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"parameter {name} must be a non-negative integer")
        applied[name] = value

    speed_min = applied.get("RIDER_SPEED_MIN", config.RIDER_SPEED_MIN)
    speed_max = applied.get("RIDER_SPEED_MAX", config.RIDER_SPEED_MAX)
    if speed_min < 1 or speed_min > speed_max:
        raise ValueError("rider speed range must satisfy 1 <= MIN <= MAX")

    for name, value in applied.items():
        setattr(config, name, value)
    return applied


class SystemManager:
    """Manages funds, the rider pool, the simulation clock and consistency.

    The state itself lives in ``globalvar``; this class provides the
    operations on that state.
    """

    @property
    def riders(self):
        """The live list of Rider objects."""
        return globalvar.get_value("riders", [])

    @property
    def funds(self):
        """Current system funds (integer, may be negative)."""
        return globalvar.get_value("funds", 0)

    @property
    def tick(self):
        """Current simulated time in ticks."""
        return globalvar.get_value("tick", 0)

    @property
    def running(self):
        """Main-loop control flag."""
        return globalvar.get_value("running", False)

    def stop(self):
        """Request the main loop to terminate."""
        globalvar.set_value("running", False)

    def adjust_funds(self, delta):
        """Add ``delta`` (may be negative) to the system funds.

        Args:
            delta: Integer amount to add.
        """
        globalvar.set_value("funds", self.funds + int(delta))

    def has_idle_rider(self):
        """Return True if at least one rider has no active orders."""
        return any(rider.is_idle for rider in self.riders)

    def can_recruit(self):
        """Return True when the pool has room and funds cover the recruit cost."""
        return (
            len(self.riders) < config.MAX_RIDERS
            and self.funds >= config.RIDER_RECRUIT_COST
        )

    def recruit_rider(self):
        """Create a new rider, charging the recruitment cost.

        Returns:
            Rider | None: The new rider, or None if recruitment is not possible.
        """
        if not self.can_recruit():
            return None
        rider_id = self._next_rider_id()
        self.adjust_funds(-config.RIDER_RECRUIT_COST)
        rider = Rider(rider_id)
        self.riders.append(rider)
        logger.info("Recruited rider %s at (%s,%s)", rider.rider_id, rider.x, rider.y)
        return rider

    def advance(self, ticks=1):
        """Advance the simulation clock and move every rider.

        A failure in one rider is logged and does not stop the simulation.

        Args:
            ticks: Number of ticks to simulate.
        """
        for _ in range(int(ticks)):
            globalvar.set_value("tick", self.tick + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception:  # noqa: BLE001 - keep the system running
                    logger.exception("Rider %s failed during tick %s", rider.rider_id, self.tick)

    def check_consistency(self):
        """Detect and repair inconsistent state.

        Repairs performed: removing completed orders from rider lists,
        snapping off-road riders onto streets, and recomputing rider states.

        Returns:
            list[str]: Descriptions of each issue found (empty when healthy).
        """
        issues = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)

            stale = [o for o in rider.orders if o.status == STATUS_COMPLETED]
            for order in stale:
                rider.orders.remove(order)
                issues.append(f"removed completed order {order.id} from rider {rider.rider_id}")

            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    issues.append(
                        f"order {order.id} owner mismatch on rider {rider.rider_id}"
                    )

            if not grid.is_on_road(rider.x, rider.y):
                old = (rider.x, rider.y)
                rider.x, rider.y = grid.snap_to_road(rider.x, rider.y)
                issues.append(f"rider {rider.rider_id} moved off-road from {old}")

            before = rider.state
            rider.refresh_state()
            if rider.state != before:
                issues.append(f"rider {rider.rider_id} state corrected to {rider.state}")

        for issue in issues:
            logger.warning("Consistency: %s", issue)
        return issues

    def snapshot(self):
        """Return a JSON-serializable snapshot of the whole system.

        Returns:
            dict: Tick, funds, rider IDs, riders, orders and parameters.
        """
        return {
            "tick": self.tick,
            "funds": self.funds,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "parameters": {name: getattr(config, name) for name in config.TUNABLE_PARAMS},
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in globalvar.get_value("orders", [])],
            "order_history": [order.to_dict() for order in globalvar.get_value("order_history", [])],
        }

    def save_state(self, path):
        """Write the system snapshot to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.snapshot(), handle, indent=2)
        logger.info("State saved to %s", path)

    def load_config(self, path):
        """Apply parameter overrides from a JSON configuration file.

        Args:
            path: Path to the configuration file.

        Returns:
            dict: Applied parameters, or an empty dict if loading failed.
        """
        try:
            return apply_config_file(path)
        except (OSError, ValueError) as exc:
            logger.warning("Could not load configuration %s: %s", path, exc)
            return {}

    def _next_rider_id(self):
        """Increment and return the rider ID counter."""
        counter = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        return counter


def init_system(config_path=None):
    """Initialize global state and return the system manager.

    Args:
        config_path: Optional JSON configuration file applied before the
            default state is created.

    Returns:
        SystemManager: The manager bound to the initialized globals.
    """
    if config_path and os.path.exists(config_path):
        try:
            applied = apply_config_file(config_path)
            logger.info("Applied configuration overrides: %s", applied)
        except (OSError, ValueError) as exc:
            logger.warning("Ignoring configuration %s: %s", config_path, exc)

    globalvar._init()
    manager = SystemManager()
    globalvar.set_value("system_manager", manager)
    logger.info("System initialized with funds %s", manager.funds)
    return manager
