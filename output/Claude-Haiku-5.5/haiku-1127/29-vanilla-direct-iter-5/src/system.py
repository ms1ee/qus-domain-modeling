"""System management: funds, rider recruitment, simulation clock and persistence."""

from __future__ import annotations

import copy
import json
import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import globalvar
from order import OrderManager, assign_order, validate_coordinates
from order_model import Order
from path_planner import PathPlanner
from rider import STATE_IDLE, Rider

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "initial_funds": 1000,
    "recruit_cost": 300,
    "recruit_threshold": 300,
    "rider_speed": 10,
    "rider_start": [435, 385],
    "max_ticks_per_run": 10000,
    "state_file": "dispatch_state.json",
}


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load system parameters from a JSON file, falling back to defaults.

    Unknown keys are ignored.  Invalid files produce a warning and defaults.

    Args:
        path: Path to the JSON config file (defaults to ``src/config.json``).

    Returns:
        The merged configuration dictionary.
    """
    config = copy.deepcopy(DEFAULT_CONFIG)
    path = path or CONFIG_FILE
    if not os.path.exists(path):
        return config
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read config %s: %s; using defaults.", path, exc)
        return config
    if not isinstance(data, dict):
        logger.warning("Config %s is not a JSON object; using defaults.", path)
        return config
    for key, value in data.items():
        if key in DEFAULT_CONFIG:
            config[key] = value
    try:
        config["initial_funds"] = int(config["initial_funds"])
        config["recruit_cost"] = int(config["recruit_cost"])
        config["recruit_threshold"] = int(config["recruit_threshold"])
        config["rider_speed"] = max(1, int(config["rider_speed"]))
        config["rider_start"] = [int(config["rider_start"][0]), int(config["rider_start"][1])]
        config["max_ticks_per_run"] = max(1, int(config["max_ticks_per_run"]))
    except (TypeError, ValueError, IndexError, KeyError) as exc:
        logger.warning("Invalid config values (%s); using defaults.", exc)
        return copy.deepcopy(DEFAULT_CONFIG)
    return config


def init_system(config_path: Optional[str] = None) -> None:
    """Initialise the global state for a fresh simulation run.

    Args:
        config_path: Optional path to a JSON configuration file.
    """
    config = load_config(config_path)
    globalvar._init()
    globalvar.set_value("config", config)
    globalvar.set_value("system_funds", config["initial_funds"])
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("system_running", True)
    globalvar.set_value("orders", [])
    globalvar.set_value("current_tick", 0)
    globalvar.set_value("rider_speed", config["rider_speed"])
    globalvar.set_value("rider_start", tuple(config["rider_start"]))
    logger.info("System initialised with funds=%d", config["initial_funds"])


class SystemManager:
    """Core coordinator for funds, riders, orders and the simulation clock."""

    def __init__(self) -> None:
        """Bind to the globally initialised system state."""
        config = globalvar.get_value("config")
        self.config: Dict[str, Any] = config if config else copy.deepcopy(DEFAULT_CONFIG)

    # ------------------------------------------------------------------ #
    # Accessors
    # ------------------------------------------------------------------ #
    @property
    def funds(self) -> int:
        """Current system funds."""
        return int(globalvar.get_value("system_funds", 0))

    def _set_funds(self, value: int) -> None:
        globalvar.set_value("system_funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """The live rider list."""
        return globalvar.get_value("riders")

    @property
    def tick_count(self) -> int:
        """Current simulation tick."""
        return int(globalvar.get_value("current_tick", 0))

    def get_rider(self, rider_id: Optional[int]) -> Optional[Rider]:
        """Return the rider with ``rider_id`` or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def idle_rider_count(self) -> int:
        """Return the number of riders that are idle and have no orders."""
        return sum(1 for rider in self.riders if rider.is_idle())

    # ------------------------------------------------------------------ #
    # Recruitment
    # ------------------------------------------------------------------ #
    def recruit_rider(self) -> Optional[Rider]:
        """Create a new rider if funds allow.

        Returns:
            The new rider, or None if funds are below the threshold.
        """
        threshold = int(self.config["recruit_threshold"])
        cost = int(self.config["recruit_cost"])
        if self.funds < threshold:
            return None
        self._set_funds(self.funds - cost)
        counter = int(globalvar.get_value("rider_id_counter", 0)) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        logger.info("Recruited rider #%d (cost %d, funds now %d)", counter, cost, self.funds)
        return rider

    def ensure_capacity(self) -> List[Rider]:
        """Recruit riders while pending orders outnumber idle riders.

        Returns:
            List of riders recruited during this call.
        """
        recruited: List[Rider] = []
        while len(OrderManager.pending_orders()) > self.idle_rider_count():
            rider = self.recruit_rider()
            if rider is None:
                break
            recruited.append(rider)
        return recruited

    def dispatch_pending(self) -> Tuple[List[Rider], List[Order]]:
        """Recruit if needed, then assign every pending order.

        Returns:
            Tuple of (riders recruited, orders that were assigned).
        """
        recruited = self.ensure_capacity()
        assigned: List[Order] = []
        for order in OrderManager.pending_orders():
            if assign_order(order) is not None:
                assigned.append(order)
        return recruited, assigned

    # ------------------------------------------------------------------ #
    # Orders and simulation
    # ------------------------------------------------------------------ #
    def submit_order(self, coordinates: Sequence[Any]) -> Dict[str, Any]:
        """Create an order from user input and dispatch it.

        Args:
            coordinates: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Returns:
            Dictionary with keys ``order``, ``rider``, ``new_riders``,
            ``distance`` (rider to restaurant), ``route`` (predicted points),
            and ``eta`` (predicted ticks, or None if the rider is busy).

        Raises:
            ValueError: If the coordinates are invalid.
        """
        validate_coordinates(coordinates)
        order = OrderManager.create_order(coordinates, self.tick_count)
        recruited, _ = self.dispatch_pending()
        rider = self.get_rider(order.rider_id) if order.rider_id is not None else None

        route: List[Tuple[int, int]] = []
        eta: Optional[int] = None
        distance = 0.0
        if rider is not None:
            distance = math.hypot(rider.x - order.res_pos[0], rider.y - order.res_pos[1])
            if rider.state == STATE_IDLE and rider.orders == [order]:
                route, eta = self.predict_route(rider, order)
        return {
            "order": order,
            "rider": rider,
            "new_riders": recruited,
            "distance": distance,
            "route": route,
            "eta": eta,
        }

    @staticmethod
    def predict_route(rider: Rider, order: Order) -> Tuple[List[Tuple[int, int]], int]:
        """Predict the path and duration of an order for an idle rider.

        The prediction follows the same rules as :meth:`Rider.move`: one tick
        to accept the order, then movement to the restaurant and to the
        customer.

        Args:
            rider: The idle rider that would execute the order.
            order: The order to simulate.

        Returns:
            Tuple of (list of positions visited, estimated ticks).
        """
        x, y = rider.position
        points: List[Tuple[int, int]] = [(x, y)]
        ticks = 1  # acceptance tick (no movement)
        for target in (order.res_pos, order.cus_pos):
            route = PathPlanner.build_route((x, y), target)
            if not route:
                ticks += 1
                continue
            while route:
                x, y = PathPlanner.advance(x, y, route, rider.speed)
                points.append((x, y))
                ticks += 1
        return points, ticks

    def tick(self) -> None:
        """Advance the simulation clock by one tick.

        Pending orders are dispatched first, then every rider moves.  A
        failing rider is recovered without stopping the other riders.
        """
        globalvar.set_value("current_tick", self.tick_count + 1)
        self.dispatch_pending()
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # error recovery: keep the simulation running
                logger.exception("Error while moving rider #%d", rider.rider_id)
                rider.recover()

    def has_active_orders(self) -> bool:
        """Return True while any order has not been completed."""
        return bool(OrderManager.active_orders())

    def run_until_idle(self, max_ticks: Optional[int] = None) -> int:
        """Tick until every order is completed.

        Args:
            max_ticks: Safety limit; defaults to the configured value.

        Returns:
            Number of ticks elapsed.

        Raises:
            RuntimeError: If the limit is reached with orders still active.
        """
        limit = int(max_ticks or self.config["max_ticks_per_run"])
        start = self.tick_count
        while self.has_active_orders():
            if self.tick_count - start >= limit:
                raise RuntimeError(
                    f"orders still active after {limit} ticks (no rider may be available)")
            self.tick()
        return self.tick_count - start

    # ------------------------------------------------------------------ #
    # Consistency and persistence
    # ------------------------------------------------------------------ #
    def check_consistency(self) -> List[str]:
        """Verify internal invariants and return a list of problems found."""
        problems: List[str] = []
        if not isinstance(self.funds, int):
            problems.append("system funds is not an integer")
        ids = [rider.rider_id for rider in self.riders]
        if len(ids) != len(set(ids)):
            problems.append("duplicate rider IDs detected")
        for rider in self.riders:
            if not (0 <= rider.x <= 800 and 0 <= rider.y <= 800):
                problems.append(f"rider #{rider.rider_id} is outside the map")
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    problems.append(
                        f"order #{order.id} is held by rider #{rider.rider_id} "
                        f"but records rider #{order.rider_id}")
        for order in OrderManager.active_orders():
            if order.rider_id is not None and self.get_rider(order.rider_id) is None:
                problems.append(f"order #{order.id} references missing rider #{order.rider_id}")
        return problems

    def save_state(self, path: Optional[str] = None) -> str:
        """Persist configuration, riders and order history as JSON.

        Args:
            path: Destination file; defaults to ``config["state_file"]``.

        Returns:
            The path that was written.

        Raises:
            OSError: If the file cannot be written.
        """
        path = path or str(self.config["state_file"])
        data = {
            "config": self.config,
            "system_funds": self.funds,
            "current_tick": self.tick_count,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [
                {
                    "rider_id": r.rider_id,
                    "x": r.x,
                    "y": r.y,
                    "speed": r.speed,
                    "state": r.state,
                    "order_ids": [o.id for o in r.orders],
                    "special_case": r.special_case,
                    "log": r.log,
                }
                for r in self.riders
            ],
            "orders": [o.to_dict() for o in OrderManager.all_orders()],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("State saved to %s", path)
        return path
