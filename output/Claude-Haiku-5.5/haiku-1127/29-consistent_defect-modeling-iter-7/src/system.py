"""System manager: funds, rider recruitment, simulated clock and persistence."""

import json
import logging
import math
import os
from typing import Any, Dict, List, Optional

import globalvar
from order import OrderManager
from order_model import STATUS_ASSIGNED, STATUS_CREATED, STATUS_PICKED_UP
from path_planner import PathPlanner
from rider import (
    STATE_DELIVERING,
    STATE_IDLE,
    STATE_PICKING_UP,
    Rider,
)

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG: Dict[str, int] = {
    "initial_funds": 1000,
    "recruit_threshold": 300,
    "recruit_cost": 500,
    "grid_size": 8,
    "cell_size": 100,
    "min_coordinate": 0,
    "max_coordinate": 800,
}


def load_config(path: str = CONFIG_PATH) -> Dict[str, int]:
    """Load system parameters from a JSON file, falling back to defaults.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        A dictionary containing every known configuration key.
    """
    config = dict(DEFAULT_CONFIG)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        logger.info("Config file %s not found; using defaults", path)
        return config
    except (OSError, ValueError) as exc:
        logger.warning("Could not read config %s (%s); using defaults", path, exc)
        return config

    if isinstance(data, dict):
        for key in DEFAULT_CONFIG:
            if key in data:
                try:
                    config[key] = int(data[key])
                except (TypeError, ValueError):
                    logger.warning("Ignoring invalid config value for %s", key)
    return config


def init_system() -> "SystemManager":
    """Reset global state and create a fully initialized SystemManager.

    Returns:
        The initialized SystemManager.
    """
    globalvar._init()
    config = load_config()
    return SystemManager(config)


class SystemManager:
    """Owns the simulation state: funds, riders, clock and orders.

    Shared values live in global storage (see ``globalvar``), so the
    properties below always reflect the same data used by every module.
    """

    def __init__(self, config: Optional[Dict[str, int]] = None) -> None:
        """Initialize core parameters.

        Args:
            config: Optional configuration overriding the defaults.
        """
        self.config: Dict[str, int] = dict(DEFAULT_CONFIG)
        if config:
            self.config.update(config)

        globalvar.set_value("funds", int(self.config["initial_funds"]))
        globalvar.set_value("riders", [])
        globalvar.set_value("rider_id_counter", 0)
        globalvar.set_value("running", True)
        globalvar.set_value("current_tick", 0)
        globalvar.set_value("orders", [])

        self.order_manager = OrderManager()
        self.planner = PathPlanner(
            grid_size=self.config["grid_size"],
            cell_size=self.config["cell_size"],
        )

    @property
    def funds(self) -> int:
        """System funds (may be negative)."""
        return int(globalvar.get_value("funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        globalvar.set_value("funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """Dynamic list of riders."""
        return globalvar.get_value("riders")

    @property
    def rider_id_counter(self) -> int:
        """Last rider identifier handed out."""
        return int(globalvar.get_value("rider_id_counter", 0))

    @rider_id_counter.setter
    def rider_id_counter(self, value: int) -> None:
        globalvar.set_value("rider_id_counter", int(value))

    @property
    def running(self) -> bool:
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("running", False))

    @running.setter
    def running(self, value: bool) -> None:
        globalvar.set_value("running", bool(value))

    @property
    def current_tick(self) -> int:
        """Current simulation tick."""
        return int(globalvar.get_value("current_tick", 0))

    @current_tick.setter
    def current_tick(self, value: int) -> None:
        globalvar.set_value("current_tick", int(value))

    def idle_count(self) -> int:
        """Return the number of riders in the idle state."""
        return sum(1 for r in self.riders if r.state == STATE_IDLE)

    def should_recruit(self, pending_count: int) -> bool:
        """Decide whether a new rider should be recruited.

        Args:
            pending_count: Number of orders waiting for pickup.

        Returns:
            True if funds are at least the threshold and pending orders
            exceed idle riders.
        """
        return (self.funds >= self.config["recruit_threshold"]
                and pending_count > self.idle_count())

    def recruit_rider(self) -> Rider:
        """Create a new rider and deduct the recruitment cost.

        Returns:
            The newly recruited Rider.
        """
        self.rider_id_counter = self.rider_id_counter + 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        self.funds = self.funds - self.config["recruit_cost"]
        logger.info("Recruited rider %d", rider.rider_id)
        return rider

    def find_rider(self, rider_id: Optional[int]) -> Optional[Rider]:
        """Return the rider with ``rider_id`` or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def build_route(self, rider: Rider, order: Any) -> List[tuple]:
        """Build the route from the rider's position through pickup to delivery.

        Args:
            rider: Rider that will serve the order.
            order: Order being planned.

        Returns:
            Ordered list of waypoints.
        """
        first = self.planner.plan(rider.position, order.restaurant_pos)
        second = self.planner.plan(order.restaurant_pos, order.customer_pos)
        return first + second[1:]

    def place_order(self, restaurant_x: int, restaurant_y: int,
                    customer_x: int, customer_y: int) -> Dict[str, Any]:
        """Create an order, possibly recruit a rider, and dispatch it.

        Args:
            restaurant_x: Restaurant x coordinate (0-800).
            restaurant_y: Restaurant y coordinate (0-800).
            customer_x: Customer x coordinate (0-800).
            customer_y: Customer y coordinate (0-800).

        Returns:
            Dictionary with keys: order, restaurant, customer,
            recruited_rider, rider, route, route_length, eta_ticks, queued.

        Raises:
            ValueError: If a coordinate is outside the allowed range.
        """
        lo = self.config["min_coordinate"]
        hi = self.config["max_coordinate"]
        for value in (restaurant_x, restaurant_y, customer_x, customer_y):
            if not lo <= int(value) <= hi:
                raise ValueError(f"coordinate {value} outside {lo}-{hi}")

        order = self.order_manager.create_order(
            (restaurant_x, restaurant_y), (customer_x, customer_y))

        pending = len(self.order_manager.pending_orders())
        recruited: Optional[Rider] = None
        if self.should_recruit(pending):
            recruited = self.recruit_rider()

        rider = self.order_manager.assign_order(order)
        route: List[tuple] = []
        route_length = 0
        eta: Optional[int] = None
        if rider is not None:
            route = self.build_route(rider, order)
            route_length = self.planner.route_length(route)
            eta = self.planner.estimate_ticks(route_length, rider.speed)

        return {
            "order": order,
            "restaurant": order.restaurant_pos,
            "customer": order.customer_pos,
            "recruited_rider": recruited,
            "rider": rider,
            "route": route,
            "route_length": route_length,
            "eta_ticks": eta,
            "queued": rider is None,
        }

    def tick(self) -> None:
        """Advance the simulation by one unit of time.

        Order:
            1. Increment the clock.
            2. Recruit a rider if queued orders justify it.
            3. Dispatch queued orders.
            4. Move every rider. Exceptions are logged and the loop continues,
               so one faulty rider cannot stop the simulation.
        """
        self.current_tick = self.current_tick + 1

        queued = [o for o in self.order_manager.orders if o.status == STATUS_CREATED]
        if queued and self.should_recruit(len(self.order_manager.pending_orders())):
            self.recruit_rider()

        try:
            self.order_manager.dispatch_pending()
        except Exception:  # pragma: no cover - defensive recovery
            logger.exception("Dispatch failed; state preserved")

        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive recovery
                logger.exception("Rider %s failed to move", rider.rider_id)

    def run_ticks(self, count: int) -> None:
        """Advance the simulation by ``count`` ticks."""
        for _ in range(count):
            self.tick()

    def stop(self) -> None:
        """Signal the main loop to exit."""
        self.running = False

    def check_consistency(self) -> List[str]:
        """Check internal state invariants.

        Returns:
            Human-readable descriptions of every inconsistency found. An empty
            list means the state is consistent.
        """
        issues: List[str] = []
        if not isinstance(self.funds, int):
            issues.append("funds is not an integer")

        ids = [r.rider_id for r in self.riders]
        if len(ids) != len(set(ids)):
            issues.append("duplicate rider identifiers detected")
        if ids and max(ids) > self.rider_id_counter:
            issues.append("rider_id_counter is behind the largest rider id")

        for rider in self.riders:
            active = rider.active_order_count()
            current = rider.current_order()
            if rider.state != STATE_IDLE and active == 0:
                issues.append(f"Rider #{rider.rider_id} is busy without orders")
            if rider.state == STATE_IDLE and any(
                    o.status == STATUS_PICKED_UP for o in rider.orders):
                issues.append(f"Rider #{rider.rider_id} is idle while carrying food")
            if rider.state == STATE_PICKING_UP and current is not None \
                    and current.status != STATUS_ASSIGNED:
                issues.append(f"Rider #{rider.rider_id} state/order mismatch")
            if rider.state == STATE_DELIVERING and current is not None \
                    and current.status != STATUS_PICKED_UP:
                issues.append(f"Rider #{rider.rider_id} state/order mismatch")
            if not (0 <= rider.x <= 800 and 0 <= rider.y <= 800):
                issues.append(f"Rider #{rider.rider_id} is off the map")

        for order in self.order_manager.orders:
            if order.status in (STATUS_ASSIGNED, STATUS_PICKED_UP):
                rider = self.find_rider(order.rider_id)
                if rider is None or order not in rider.orders:
                    issues.append(f"Order #{order.id} is not held by its rider")
        return issues

    def save_state(self, path: str) -> None:
        """Persist parameters, riders and order history as JSON.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        data = {
            "config": self.config,
            "funds": self.funds,
            "rider_id_counter": self.rider_id_counter,
            "current_tick": self.current_tick,
            "riders": [
                {
                    "rider_id": r.rider_id,
                    "x": r.x,
                    "y": r.y,
                    "speed": r.speed,
                    "state": r.state,
                    "special_case": r.special_case,
                    "order_ids": [o.id for o in r.orders],
                    "log": r.log,
                }
                for r in self.riders
            ],
            "orders": [o.to_dict() for o in self.order_manager.orders],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("State saved to %s", path)
