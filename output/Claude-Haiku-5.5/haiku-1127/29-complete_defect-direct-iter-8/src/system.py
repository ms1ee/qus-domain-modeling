"""System-level management: funds, rider recruitment, ticks and persistence."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import globalvar
from order import OrderManager
from path_planner import CELL_SIZE, GRID_SIZE, MAP_SIZE
from rider import IDLE, Rider

logger = logging.getLogger("dispatch.system")


def init_system() -> None:
    """Initialise all core parameters on system startup.

    Resets the global store: empty rider list, rider ID counter 0,
    running state True, zero funds, tick 0, empty order list, default
    configuration, and the 8x8 grid description.
    """
    globalvar._init()
    globalvar.set_value("grid", {
        "size": GRID_SIZE,
        "cell_size": CELL_SIZE,
        "map_size": MAP_SIZE,
    })
    logger.info("System initialised")


class SystemManager:
    """Manages funds, riders, orders, the simulation clock and persistence."""

    def __init__(self) -> None:
        """Create the manager; call :func:`init_system` beforehand."""
        self.order_manager = OrderManager()

    # ----- funds and configuration -------------------------------------
    @property
    def funds(self) -> int:
        """Return the current system fund balance."""
        return int(globalvar.get_value("funds", 0))

    def add_funds(self, amount: int) -> int:
        """Add ``amount`` (may be negative) to the fund balance.

        Args:
            amount: Integer amount to add.

        Returns:
            The new fund balance.
        """
        new_value = self.funds + int(amount)
        globalvar.set_value("funds", new_value)
        return new_value

    def _config(self, key: str, default: int) -> int:
        """Read an integer configuration value."""
        config = globalvar.get_value("config") or {}
        return int(config.get(key, default))

    # ----- rider CRUD ----------------------------------------------------
    @property
    def riders(self) -> List[Rider]:
        """Return the live rider list."""
        return globalvar.get_value("riders")

    def get_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with ``rider_id``, or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def create_rider(self) -> Rider:
        """Create a new idle rider with the next unique ID.

        Returns:
            The newly created Rider.
        """
        counter = int(globalvar.get_value("rider_id_counter", 0)) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        logger.info("Recruited rider %s", counter)
        return rider

    def remove_rider(self, rider_id: int) -> bool:
        """Remove an idle rider with no assigned orders.

        Args:
            rider_id: ID of the rider to remove.

        Returns:
            True if the rider was removed, False otherwise.
        """
        rider = self.get_rider(rider_id)
        if rider is None or rider.orders:
            return False
        self.riders.remove(rider)
        logger.info("Removed rider %s", rider_id)
        return True

    def recruit_riders(self) -> List[Rider]:
        """Recruit riders while funds are at or above the threshold.

        Each recruit costs ``recruit_cost`` from the fund balance.

        Returns:
            List of riders created by this call.
        """
        threshold = self._config("recruit_threshold", 300)
        cost = self._config("recruit_cost", 300)
        new_riders: List[Rider] = []
        if cost <= 0:
            return new_riders
        while self.funds >= threshold:
            self.add_funds(-cost)
            new_riders.append(self.create_rider())
        return new_riders

    # ----- orders --------------------------------------------------------
    def submit_order(self, restaurant_pos, customer_pos) -> Dict[str, Any]:
        """Create an order, charge the customer, recruit and assign.

        Args:
            restaurant_pos: ``(x, y)`` restaurant coordinates.
            customer_pos: ``(x, y)`` customer coordinates.

        Returns:
            Dictionary with keys "order", "rider" (Rider or None),
            "new_riders" (list) and "new_rider" (bool).
        """
        order = self.order_manager.create_order(restaurant_pos, customer_pos)
        self.add_funds(order.fee)
        new_riders = self.recruit_riders()
        rider = self.order_manager.assign_order(order)
        return {
            "order": order,
            "rider": rider,
            "new_riders": new_riders,
            "new_rider": bool(new_riders),
        }

    # ----- simulation clock ----------------------------------------------
    @property
    def tick_count(self) -> int:
        """Return the current simulated tick."""
        return int(globalvar.get_value("tick", 0))

    def tick(self) -> int:
        """Advance the simulation by one unit of time.

        Assigns pending orders, then moves every rider. Exceptions in a
        single rider are logged and that rider is reset to a safe state so
        the rest of the system keeps running.

        Returns:
            The new tick value.
        """
        globalvar.set_value("tick", self.tick_count + 1)
        try:
            self.order_manager.assign_pending_orders()
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to assign pending orders")
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:
                logger.exception("Rider %s failed; recovering", rider.rider_id)
                self._recover_rider(rider)
        return self.tick_count

    def _recover_rider(self, rider: Rider) -> None:
        """Reset a rider to a consistent idle state after an error."""
        for order in rider.orders:
            if order.status in ("pickup", "delivering"):
                order.status = "assigned"
        rider.state = IDLE
        rider.path = []
        rider.special_case = False

    # ----- consistency ---------------------------------------------------
    def check_consistency(self) -> List[str]:
        """Check internal state consistency.

        Returns:
            List of human-readable problems; empty when consistent.
        """
        issues: List[str] = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                issues.append(f"Duplicate rider ID {rider.rider_id}")
            seen_ids.add(rider.rider_id)
            if rider.state not in (0, 1, 2):
                issues.append(f"Rider {rider.rider_id} has invalid state")
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    issues.append(
                        f"Order {order.id} not linked to rider {rider.rider_id}")
                if order.status == "completed":
                    issues.append(
                        f"Completed order {order.id} still held by rider "
                        f"{rider.rider_id}")
        if not isinstance(globalvar.get_value("funds"), int):
            issues.append("Fund balance is not an integer")
        for order in globalvar.get_value("orders", []):
            if order.rider_id is not None and self.get_rider(order.rider_id) is None:
                if order.status != "completed":
                    issues.append(
                        f"Order {order.id} references missing rider "
                        f"{order.rider_id}")
        return issues

    # ----- persistence ---------------------------------------------------
    def save_state(self, path: str) -> None:
        """Write system parameters, riders and orders to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        data = {
            "funds": self.funds,
            "tick": self.tick_count,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "config": dict(globalvar.get_value("config") or {}),
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict()
                       for order in globalvar.get_value("orders", [])],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("State saved to %s", path)

    def load_config(self, path: str) -> Dict[str, Any]:
        """Load system parameters from a JSON configuration file.

        The file may either hold the parameters at top level or inside a
        "config" object. Unknown keys are ignored and invalid values fall
        back to the current setting. A missing file keeps the defaults.

        Args:
            path: Configuration file path.

        Returns:
            The active configuration dictionary.
        """
        config = dict(globalvar.get_value("config") or {})
        if not os.path.exists(path):
            logger.info("Config file %s not found; using defaults", path)
            return config
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read config %s: %s", path, exc)
            return config
        if not isinstance(data, dict):
            logger.warning("Config %s must contain a JSON object", path)
            return config

        source = data.get("config") if isinstance(data.get("config"), dict) \
            else data
        minimums = {
            "recruit_threshold": 0,
            "recruit_cost": 1,
            "order_fee": 0,
            "rider_speed": 1,
            "max_orders_per_rider": 1,
        }
        for key, minimum in minimums.items():
            value = source.get(key)
            if isinstance(value, int) and not isinstance(value, bool) \
                    and value >= minimum:
                config[key] = value
            elif value is not None:
                logger.warning("Ignoring invalid config value %s=%r", key, value)
        globalvar.set_value("config", config)
        return config
