"""System-level resource management.

Responsibilities:
    * Holding the fund balance, rider pool, ID counter and simulation clock.
    * Automatic rider recruitment (funds >= threshold and pending orders
      exceed idle riders).
    * Dispatching pending orders and advancing the simulation by ticks.
    * Consistency checks, error recovery and JSON state persistence.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from order import OrderManager, find_best_rider_for_order
from order_model import COMPLETED, PENDING, Order
from path_planner import MAP_SIZE, clamp_to_cell_corner, is_street_point
from rider import STATE_IDLE, STATE_NAMES, Rider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "initial_funds": 1000,
    "recruit_min_funds": 300,
    "recruit_cost": 500,
    "rider_speed": 20,
    "spawn_position": [400, 400],
}


def _load_parameters(path: str) -> Dict[str, Any]:
    """Read system parameters from a JSON configuration file.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        Dictionary of recognised parameters (possibly empty).
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        params = data.get("parameters", {}) if isinstance(data, dict) else {}
        return {key: params[key] for key in DEFAULT_CONFIG if key in params}
    except (OSError, ValueError, AttributeError) as exc:
        logger.warning("Could not read configuration %s: %s", path, exc)
        return {}


def init_system(config_path: Optional[str] = None) -> "SystemManager":
    """Initialise global state and return a ready ``SystemManager``.

    Args:
        config_path: Optional JSON configuration file. Missing or invalid
            files fall back to the built-in defaults.

    Returns:
        A new ``SystemManager`` bound to the freshly reset global store.
    """
    globalvar._init()
    config = dict(DEFAULT_CONFIG)
    if config_path and os.path.exists(config_path):
        config.update(_load_parameters(config_path))
    globalvar.set_value("config", config)
    globalvar.set_value("system_funds", int(config["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("pending_orders", [])
    globalvar.set_value("orders", [])
    globalvar.set_value("sim_time", 0)
    globalvar.set_value("system_running", True)
    logger.info("System initialised with funds=%s", config["initial_funds"])
    return SystemManager()


class SystemManager:
    """Core coordinator for funds, riders, orders and simulated time."""

    def __init__(self) -> None:
        """Create the manager; global state must already be initialised."""
        self.order_manager = OrderManager()

    # ------------------------------------------------------------------ #
    # Accessors backed by the global store
    # ------------------------------------------------------------------ #
    @property
    def config(self) -> Dict[str, Any]:
        """System parameters."""
        return globalvar.get_value("config") or dict(DEFAULT_CONFIG)

    @property
    def funds(self) -> int:
        """Current fund balance (may be negative)."""
        return int(globalvar.get_value("system_funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        globalvar.set_value("system_funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """Dynamic rider pool."""
        return globalvar.get_value("riders")

    @property
    def pending_orders(self) -> List[Order]:
        """Orders waiting for a rider."""
        return globalvar.get_value("pending_orders")

    @property
    def sim_time(self) -> int:
        """Current simulation tick."""
        return int(globalvar.get_value("sim_time", 0))

    @property
    def running(self) -> bool:
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("system_running", False))

    # ------------------------------------------------------------------ #
    # Recruitment and dispatch
    # ------------------------------------------------------------------ #
    def idle_rider_count(self) -> int:
        """Number of riders with no active orders."""
        return sum(1 for rider in self.riders if not rider.active_orders())

    def recruit_rider(self) -> Rider:
        """Create a new rider, deduct the recruitment cost and register it.

        Returns:
            The newly recruited rider.
        """
        cfg = self.config
        new_id = int(globalvar.get_value("rider_id_counter", 0)) + 1
        globalvar.set_value("rider_id_counter", new_id)
        self.funds = self.funds - int(cfg["recruit_cost"])
        rider = Rider(
            new_id,
            speed=int(cfg["rider_speed"]),
            position=tuple(cfg["spawn_position"]),
        )
        self.riders.append(rider)
        logger.info("Recruited rider %s; funds now %s", new_id, self.funds)
        return rider

    def submit_order(self, order: Order) -> Tuple[Optional[Rider], bool]:
        """Queue ``order`` and dispatch as many pending orders as possible.

        Args:
            order: Newly created order.

        Returns:
            Tuple ``(rider, recruited)``: the rider assigned to ``order`` (None
            if it stays pending) and whether a new rider was recruited.
        """
        self.pending_orders.append(order)
        assignments, recruited = self._dispatch_pending()
        for assigned_order, rider in assignments:
            if assigned_order is order:
                return rider, recruited
        return None, recruited

    def _dispatch_pending(self) -> Tuple[List[Tuple[Order, Rider]], bool]:
        """Recruit when needed, then assign pending orders to riders.

        Recruitment rule: while funds >= recruit_min_funds and the number of
        pending orders exceeds the number of idle riders, recruit a rider.

        Returns:
            Tuple ``(assignments, recruited)``.
        """
        cfg = self.config
        recruited = False
        while (
            self.pending_orders
            and self.funds >= int(cfg["recruit_min_funds"])
            and len(self.pending_orders) > self.idle_rider_count()
        ):
            self.recruit_rider()
            recruited = True

        assignments: List[Tuple[Order, Rider]] = []
        for order in list(self.pending_orders):
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            self.order_manager.assign_order(order, rider)
            self.pending_orders.remove(order)
            assignments.append((order, rider))
        return assignments, recruited

    # ------------------------------------------------------------------ #
    # Simulation loop
    # ------------------------------------------------------------------ #
    def tick(self) -> None:
        """Advance the simulation by one unit of time.

        Steps: dispatch pending orders, move every rider, then increment the
        clock. A failing rider is recovered rather than crashing the loop.
        """
        try:
            self._dispatch_pending()
        except Exception:  # noqa: BLE001 - keep the simulation alive
            logger.exception("Dispatch failed during tick %s", self.sim_time)

        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # noqa: BLE001 - error recovery
                logger.exception("Rider %s failed during tick %s", rider.rider_id, self.sim_time)
                self._recover_rider(rider)

        globalvar.set_value("sim_time", self.sim_time + 1)

    def _recover_rider(self, rider: Rider) -> None:
        """Restore a rider to a consistent state after an unexpected error."""
        rider.state = STATE_IDLE
        rider.special_case = False
        if not is_street_point(rider.x, rider.y):
            rider.y = clamp_to_cell_corner(rider.y)
        rider.x = max(0, min(MAP_SIZE, rider.x))
        rider.y = max(0, min(MAP_SIZE, rider.y))
        logger.warning("Rider %s recovered to idle at (%s,%s)", rider.rider_id, rider.x, rider.y)

    def check_consistency(self) -> List[str]:
        """Validate internal invariants and return a list of problems.

        Returns:
            Human-readable issue descriptions; an empty list means healthy.
        """
        issues: List[str] = []
        if not isinstance(self.funds, int):
            issues.append("system funds is not an integer")
        ids = [rider.rider_id for rider in self.riders]
        if len(ids) != len(set(ids)):
            issues.append("duplicate rider IDs detected")
        counter = int(globalvar.get_value("rider_id_counter", 0))
        if ids and max(ids) > counter:
            issues.append("rider ID counter is behind the highest rider ID")
        for rider in self.riders:
            if not (0 <= rider.x <= MAP_SIZE and 0 <= rider.y <= MAP_SIZE):
                issues.append(f"rider #{rider.rider_id} is outside the map")
            if not is_street_point(rider.x, rider.y):
                issues.append(f"rider #{rider.rider_id} is off the street grid")
            if rider.state not in STATE_NAMES:
                issues.append(f"rider #{rider.rider_id} has unknown state {rider.state}")
            if rider.state != STATE_IDLE and not rider.active_orders():
                issues.append(f"rider #{rider.rider_id} is busy without active orders")
        for order in self.order_manager.orders:
            if order.status == COMPLETED and order.completion_time is None:
                issues.append(f"order #{order.id} completed without completion time")
        for order in self.pending_orders:
            if order.status != PENDING:
                issues.append(f"pending order #{order.id} has status {order.status}")
        return issues

    # ------------------------------------------------------------------ #
    # Persistence and shutdown
    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        """Return the full system state as a JSON-serialisable dictionary."""
        return {
            "parameters": dict(self.config),
            "system_funds": self.funds,
            "rider_id_counter": int(globalvar.get_value("rider_id_counter", 0)),
            "sim_time": self.sim_time,
            "pending_order_ids": [order.id for order in self.pending_orders],
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.order_manager.orders],
        }

    def save_state(self, path: str) -> str:
        """Write the system state to a JSON file.

        Args:
            path: Destination file path.

        Returns:
            The path that was written.

        Raises:
            OSError: If the file cannot be written.
        """
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
        logger.info("State saved to %s", path)
        return path

    def shutdown(self) -> None:
        """Stop the main loop."""
        globalvar.set_value("system_running", False)
        logger.info("System shut down at tick %s", self.sim_time)
