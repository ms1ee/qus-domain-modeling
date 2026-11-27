"""System-level resource management: funds, riders and simulation ticks."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from order import OrderManager
from rider import Rider

logger = logging.getLogger(__name__)

DEFAULT_PARAMETERS: Dict[str, int] = {
    "initial_funds": 1000,
    "recruit_funds_threshold": 300,
    "recruit_cost": 500,
}


def init_system() -> None:
    """Initialize core global parameters on system startup.

    Sets funds to 1000, an empty rider list, the rider ID counter to 0, the
    running flag to True, the tick to 0 and an empty order list.
    """
    globalvar._init()
    globalvar.set_value("funds", DEFAULT_PARAMETERS["initial_funds"])
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    logger.info("System initialized")


class SystemManager:
    """Coordinates funds, rider recruitment, order dispatch and ticks."""

    def __init__(self) -> None:
        """Initialize the system and its order manager."""
        init_system()
        self.params: Dict[str, int] = dict(DEFAULT_PARAMETERS)
        self.order_manager = OrderManager()

    # ----- global state accessors -------------------------------------
    @property
    def funds(self) -> int:
        """Current system funds (may be negative)."""
        return globalvar.get_value("funds", 0)

    @funds.setter
    def funds(self, value: int) -> None:
        globalvar.set_value("funds", value)

    @property
    def riders(self) -> List[Rider]:
        """List of all riders currently in service."""
        return globalvar.get_value("riders", [])

    @property
    def tick_count(self) -> int:
        """Number of simulated ticks elapsed."""
        return globalvar.get_value("tick", 0)

    @property
    def running(self) -> bool:
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("running", False))

    def stop(self) -> None:
        """Signal the main loop to stop."""
        globalvar.set_value("running", False)

    def get_rider(self, rider_id: int) -> Optional[Rider]:
        """Find a rider by ID.

        Args:
            rider_id: Identifier of the rider.

        Returns:
            The matching rider, or None.
        """
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def idle_riders(self) -> List[Rider]:
        """Return riders that currently have no active orders."""
        return [r for r in self.riders if not r.active_orders()]

    def pending_count(self) -> int:
        """Return the number of orders waiting for assignment."""
        return len(self.order_manager.pending_orders())

    # ----- recruitment -----------------------------------------------
    def add_rider(self) -> Rider:
        """Recruit a new rider, deducting the recruitment cost.

        Returns:
            The newly created rider.
        """
        counter = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        self.funds = self.funds - self.params["recruit_cost"]
        logger.info("Recruited rider %s (funds now %s)", counter, self.funds)
        return rider

    def maybe_recruit(self) -> int:
        """Recruit riders while funds allow and pending orders exceed idle riders.

        Returns:
            Number of riders recruited.
        """
        count = 0
        while (self.funds >= self.params["recruit_funds_threshold"]
               and self.pending_count() > len(self.idle_riders())):
            self.add_rider()
            count += 1
        return count

    # ----- dispatch --------------------------------------------------
    def dispatch(self) -> List[Any]:
        """Recruit if needed and assign all pending orders.

        Returns:
            List of ``(order, rider)`` pairs assigned in this call.
        """
        self.maybe_recruit()
        return self.order_manager.assign_pending_orders()

    def submit_order(self, restaurant_xy: Tuple[int, int],
                     customer_xy: Tuple[int, int]) -> Dict[str, Any]:
        """Create an order, recruit if necessary and assign it.

        Args:
            restaurant_xy: Restaurant input coordinate.
            customer_xy: Customer input coordinate.

        Returns:
            Dict with keys ``"order"``, ``"new_rider"`` (bool) and
            ``"rider"`` (assigned Rider or None).
        """
        order = self.order_manager.create_order(restaurant_xy, customer_xy)
        recruited = self.maybe_recruit()
        self.order_manager.assign_pending_orders()
        rider = None
        if order.rider_id is not None:
            rider = self.get_rider(order.rider_id)
        return {"order": order, "new_rider": recruited > 0, "rider": rider}

    def tick(self) -> int:
        """Advance the simulation by one tick.

        Increments the tick counter, dispatches pending orders and moves
        every rider. Errors for a single rider are logged and do not stop
        the simulation.

        Returns:
            Number of log events produced by riders during this tick.
        """
        globalvar.set_value("tick", self.tick_count + 1)
        self.dispatch()
        events = 0
        for rider in list(self.riders):
            before = len(rider.log)
            try:
                rider.move()
            except Exception:  # error recovery: keep the system running
                logger.exception("Rider %s failed to move", rider.rider_id)
            events += len(rider.log) - before
        return events

    # ----- persistence -----------------------------------------------
    def save_state(self, path: str) -> None:
        """Write parameters, riders and orders to a JSON file.

        Args:
            path: Destination file path.
        """
        data = {
            "parameters": dict(self.params),
            "system": {
                "funds": self.funds,
                "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
                "tick": self.tick_count,
            },
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.all_orders()],
        }
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp_path, path)
        logger.info("State saved to %s", path)

    def load_config(self, path: str) -> Dict[str, int]:
        """Load system parameters from a JSON configuration file.

        Only known parameter keys are applied. If ``initial_funds`` is
        provided, system funds are reset to that value.

        Args:
            path: Path of the JSON configuration file.

        Returns:
            The effective parameter dictionary.

        Raises:
            ValueError: If the file does not contain valid parameters.
        """
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        params = data.get("parameters", data)
        if not isinstance(params, dict):
            raise ValueError("Configuration 'parameters' must be an object")
        for key in DEFAULT_PARAMETERS:
            if key in params:
                value = params[key]
                if not isinstance(value, int) or isinstance(value, bool):
                    raise ValueError(f"Parameter '{key}' must be an integer")
                self.params[key] = value
        if "initial_funds" in params:
            self.funds = self.params["initial_funds"]
        logger.info("Configuration loaded from %s", path)
        return dict(self.params)
