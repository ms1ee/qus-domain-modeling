"""System resource management: funds, rider roster, simulated clock and persistence."""

import json
import logging
from typing import Any, Dict, List, Optional

import globalvar
from globalvar import PARAMS, get_value, set_value
from rider import Rider

logger = logging.getLogger(__name__)


def init_system() -> None:
    """Initialise all core parameters to their startup defaults.

    Resets the global store: funds set to the initial amount, rider list
    empty, rider ID counter at 0, running state True and the clock at tick 0.
    """
    globalvar._init()
    logger.info("System initialised with funds=%s", PARAMS["initial_funds"])


class SystemManager:
    """Manages funds, the rider roster, the simulated clock and system state.

    All state lives in the global store (see ``globalvar``), so instances
    are lightweight and may be recreated freely.
    """

    # ----- funds -----------------------------------------------------------
    @property
    def funds(self) -> int:
        """Current system fund balance (may be negative)."""
        return int(get_value("system_funds", 0))

    def adjust_funds(self, delta: int) -> int:
        """Add ``delta`` to the fund balance and return the new balance.

        Args:
            delta: Signed amount to add.
        """
        new_balance = self.funds + int(delta)
        set_value("system_funds", new_balance)
        return new_balance

    # ----- clock and run state --------------------------------------------
    @property
    def tick(self) -> int:
        """Current simulated time in ticks."""
        return int(get_value("tick", 0))

    def is_running(self) -> bool:
        """Return True while the main loop should keep running."""
        return bool(get_value("running", False))

    def stop(self) -> None:
        """Request the main loop to terminate."""
        set_value("running", False)

    def advance_tick(self) -> int:
        """Advance the simulation by one tick and move every rider.

        Returns:
            The new tick value.
        """
        new_tick = self.tick + 1
        set_value("tick", new_tick)
        for rider in list(self.riders):
            rider.move()
        return new_tick

    # ----- rider roster (CRUD) --------------------------------------------
    @property
    def riders(self) -> List[Rider]:
        """The live rider list stored in the global store."""
        riders = get_value("riders")
        if riders is None:
            riders = []
            set_value("riders", riders)
        return riders

    def get_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with ``rider_id``, or None if not found."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def recruit_rider(self) -> Optional[Rider]:
        """Create a new rider if funds allow and the roster is not full.

        The recruitment cost is deducted from system funds.

        Returns:
            The new rider, or None when funds are insufficient.
        """
        cost = PARAMS["recruit_cost"]
        if self.funds < cost:
            logger.warning("Recruitment skipped: funds %s < cost %s", self.funds, cost)
            return None
        counter = int(get_value("rider_id_counter", 0)) + 1
        set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        self.adjust_funds(-cost)
        logger.info("Recruited rider %d; funds now %d", counter, self.funds)
        return rider

    def ensure_idle_rider(self) -> Optional[Rider]:
        """Recruit a rider when no idle rider exists and capacity allows.

        Returns:
            The newly recruited rider, or None if no recruitment happened.
        """
        if any(not rider.orders for rider in self.riders):
            return None
        if len(self.riders) >= PARAMS["max_riders"]:
            return None
        return self.recruit_rider()

    def remove_rider(self, rider_id: int) -> bool:
        """Remove an idle rider from the roster.

        Args:
            rider_id: Identifier of the rider to remove.

        Returns:
            True if removed; False if the rider is missing or still has orders.
        """
        rider = self.get_rider(rider_id)
        if rider is None or rider.orders:
            return False
        self.riders.remove(rider)
        logger.info("Removed rider %d", rider_id)
        return True

    # ----- consistency -----------------------------------------------------
    def check_consistency(self) -> List[str]:
        """Check internal invariants and return a list of problem descriptions.

        Returns:
            Empty list when the state is consistent.
        """
        issues: List[str] = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)
            if rider.state not in (0, 1, 2):
                issues.append(f"rider {rider.rider_id} has invalid state {rider.state}")
            if rider.state == 2 and not rider.orders:
                issues.append(f"rider {rider.rider_id} is delivering with no orders")
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    issues.append(
                        f"order {order.id} is queued on rider {rider.rider_id} "
                        f"but assigned to {order.rider_id}"
                    )
                if order.status == "completed":
                    issues.append(f"completed order {order.id} still queued on rider {rider.rider_id}")
        return issues


def load_config(path: str) -> None:
    """Load system parameter overrides from a JSON file.

    The file may be a flat object or contain a ``"params"`` object.  Only keys
    already present in ``PARAMS`` are applied.

    Args:
        path: Path to the JSON configuration file.

    Raises:
        ValueError: If the file cannot be read or contains invalid values.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read configuration '{path}': {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("configuration root must be a JSON object")
    params = data.get("params", data)
    if not isinstance(params, dict):
        raise ValueError("'params' must be a JSON object")
    for key, value in params.items():
        if key not in PARAMS:
            continue
        try:
            PARAMS[key] = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"parameter '{key}' must be an integer") from exc
        logger.info("Configuration override %s=%s", key, PARAMS[key])


def save_snapshot(path: str) -> str:
    """Write the full system state (parameters, funds, riders, orders) to JSON.

    Args:
        path: Destination file path.

    Returns:
        The path written.

    Raises:
        OSError: If the file cannot be written.
    """
    data: Dict[str, Any] = {
        "tick": int(get_value("tick", 0)),
        "system_funds": int(get_value("system_funds", 0)),
        "rider_id_counter": int(get_value("rider_id_counter", 0)),
        "params": dict(PARAMS),
        "riders": [rider.to_dict() for rider in get_value("riders", [])],
        "orders": [order.to_dict() for order in get_value("orders", [])],
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    logger.info("Snapshot saved to %s", path)
    return path
