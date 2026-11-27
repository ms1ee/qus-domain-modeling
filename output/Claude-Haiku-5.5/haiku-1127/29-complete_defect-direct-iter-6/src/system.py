"""System initialisation, fund management, rider recruitment and simulation loop."""

import json
import logging

import globalvar
from order import OrderManager
from rider import Rider

logger = logging.getLogger("dispatch.system")

CONFIG_KEYS = (
    "initial_funds",
    "recruit_threshold",
    "recruit_cost",
    "delivery_fee",
    "default_speed",
    "max_ticks_per_order",
)


def load_config(path):
    """Load system parameters from a JSON configuration file.

    Args:
        path: Path to a JSON object containing any subset of CONFIG_KEYS.

    Returns:
        Dict of the parameters that were applied.

    Raises:
        ValueError: If the file is not a JSON object or a value is not an integer.
        OSError: If the file cannot be read.
    """
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"configuration in {path} must be a JSON object")
    applied = {}
    for key in CONFIG_KEYS:
        if key in data:
            value = data[key]
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"config '{key}' must be an integer")
            globalvar.set_value(key, value)
            applied[key] = value
    return applied


def init_system(config_path=None):
    """Initialise global state at startup.

    Sets the rider list to empty, the rider ID counter to 0, the system to
    running and simulated time to 0. Optionally applies a configuration file;
    if it cannot be loaded, defaults are kept and a warning is logged.

    Args:
        config_path: Optional path to a JSON configuration file.
    """
    globalvar._init()
    if config_path is not None:
        try:
            load_config(config_path)
            logger.info("configuration loaded from %s", config_path)
        except (OSError, ValueError) as exc:
            logger.warning("could not load configuration: %s; using defaults", exc)
    globalvar.set_value("funds", int(globalvar.get_value("initial_funds", 300)))
    globalvar.set_value("running", True)


class SystemManager:
    """Manages funds, riders, recruitment, the tick loop and persistence."""

    def __init__(self):
        """Create a manager bound to the global state."""
        self.order_manager = OrderManager()

    # ----- funds -----------------------------------------------------------
    @property
    def funds(self):
        """Return the current system fund balance."""
        return int(globalvar.get_value("funds", 0))

    def add_funds(self, amount):
        """Add ``amount`` (may be negative) to the fund balance."""
        globalvar.set_value("funds", self.funds + int(amount))

    # ----- riders ----------------------------------------------------------
    def riders(self):
        """Return the list of active riders."""
        return globalvar.get_value("riders", [])

    def get_rider(self, rider_id):
        """Return the rider with ``rider_id`` or None."""
        return next((r for r in self.riders() if r.rider_id == rider_id), None)

    def recruit_rider(self):
        """Create a new idle rider with an auto-incremented ID.

        Returns:
            The new Rider.
        """
        rider_id = int(globalvar.get_value("rider_id_counter", 0)) + 1
        globalvar.set_value("rider_id_counter", rider_id)
        rider = Rider(rider_id)
        self.riders().append(rider)
        logger.info("rider %s recruited", rider_id)
        return rider

    def check_recruitment(self):
        """Recruit riders while funds are at or above the threshold.

        Each recruit costs ``recruit_cost`` from the fund balance.

        Returns:
            List of newly recruited Rider objects (empty if none).
        """
        threshold = int(globalvar.get_value("recruit_threshold", 300))
        cost = max(1, int(globalvar.get_value("recruit_cost", 300)))
        new_riders = []
        while self.funds >= threshold:
            new_riders.append(self.recruit_rider())
            self.add_funds(-cost)
        return new_riders

    # ----- simulation ------------------------------------------------------
    def is_running(self):
        """Return the main-loop running flag."""
        return bool(globalvar.get_value("running", True))

    def stop(self):
        """Request that the main loop terminate."""
        globalvar.set_value("running", False)

    def tick(self):
        """Advance the whole system by one unit of simulated time.

        Order: recruitment check, pending-order assignment, rider movement,
        then the tick counter increments. Exceptions in one rider are logged
        and that rider is recovered without stopping the others.
        """
        if not self.is_running():
            return
        try:
            self.check_recruitment()
            self.order_manager.assign_pending()
        except Exception:  # pragma: no cover - defensive
            logger.exception("error during recruitment or assignment")
        for rider in list(self.riders()):
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive
                logger.exception("error while moving rider %s", rider.rider_id)
                rider.recover()
        globalvar.set_value("tick", int(globalvar.get_value("tick", 0)) + 1)

    def run_until_complete(self, order, max_ticks=None):
        """Run ticks until ``order`` is completed or the tick budget is spent.

        Args:
            order: The Order to follow.
            max_ticks: Maximum number of ticks; defaults to the configured value.

        Returns:
            True if the order was completed, otherwise False.
        """
        if max_ticks is None:
            max_ticks = int(globalvar.get_value("max_ticks_per_order", 2000))
        for _ in range(max_ticks):
            if order.status == "completed":
                break
            self.tick()
        return order.status == "completed"

    # ----- consistency -----------------------------------------------------
    def check_consistency(self):
        """Verify internal state invariants.

        Returns:
            List of human-readable problem descriptions (empty when consistent).
        """
        issues = []
        if not isinstance(globalvar.get_value("funds"), int):
            issues.append("funds is not an integer")
        ids = [r.rider_id for r in self.riders()]
        if len(ids) != len(set(ids)):
            issues.append("duplicate rider IDs detected")
        rider_ids = set(ids)
        for rider in self.riders():
            if rider.state not in (0, 1, 2):
                issues.append(f"rider {rider.rider_id} has invalid state {rider.state}")
            if rider.state == 0 and any(
                o.status in ("picking_up", "delivering") for o in rider.orders
            ):
                issues.append(f"rider {rider.rider_id} is idle while an order is active")
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    issues.append(f"order {order.id} is held by rider {rider.rider_id} but records another rider")
        for order in globalvar.get_value("orders", []):
            if order.rider_id is not None and order.rider_id not in rider_ids:
                if order.status != "completed":
                    issues.append(f"order {order.id} references missing rider {order.rider_id}")
        return issues

    # ----- persistence -----------------------------------------------------
    def save_state(self, path):
        """Write parameters, riders and order history to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        data = {
            "config": {key: globalvar.get_value(key) for key in CONFIG_KEYS},
            "funds": self.funds,
            "tick": globalvar.get_value("tick", 0),
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [
                {
                    "rider_id": r.rider_id,
                    "x": r.x,
                    "y": r.y,
                    "speed": r.speed,
                    "state": r.state,
                    "orders": [o.id for o in r.orders],
                    "special_case": r.special_case,
                    "distance_travelled": r.distance_travelled,
                }
                for r in self.riders()
            ],
            "orders": [o.to_dict() for o in globalvar.get_value("orders", [])],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("state saved to %s", path)
