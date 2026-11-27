"""System management: funds, rider roster, simulated clock and recovery."""

import logging

import globalvar
import order_model
from rider import Rider, IDLE

logger = logging.getLogger(__name__)

RECRUIT_COST = 500
MAX_RIDERS = 20
OPERATING_COST_PER_BUSY_TICK = 1


class SystemManager:
    """Manages funds, the rider list and the simulation clock."""

    @property
    def funds(self):
        """Current system fund balance (integer, may be negative)."""
        return globalvar.get_value("funds") or 0

    @property
    def tick_count(self):
        """Current simulated tick."""
        return globalvar.get_value("tick") or 0

    @property
    def riders(self):
        """The live list of riders."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def running(self):
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("running"))

    def add_funds(self, amount):
        """Add ``amount`` (may be negative) to the funds.

        Returns:
            The new fund balance.
        """
        new_value = self.funds + int(amount)
        globalvar.set_value("funds", new_value)
        return new_value

    def get_rider(self, rider_id):
        """Return the rider with ``rider_id`` or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def recruit_rider(self):
        """Create a new rider if funds and capacity allow.

        Returns:
            The new :class:`rider.Rider`, or None if recruitment is not possible.
        """
        if len(self.riders) >= MAX_RIDERS:
            logger.info("Recruitment skipped: maximum of %s riders reached", MAX_RIDERS)
            return None
        if self.funds < RECRUIT_COST:
            logger.info("Recruitment skipped: insufficient funds (%s)", self.funds)
            return None
        new_id = (globalvar.get_value("rider_id_counter") or 0) + 1
        globalvar.set_value("rider_id_counter", new_id)
        self.add_funds(-RECRUIT_COST)
        rider = Rider(new_id)
        self.riders.append(rider)
        logger.info("Recruited rider %s; funds now %s", new_id, self.funds)
        return rider

    def remove_rider(self, rider_id):
        """Remove an available (idle, no orders) rider.

        Returns:
            True if the rider was removed.
        """
        rider = self.get_rider(rider_id)
        if rider is None or not rider.is_available():
            return False
        self.riders.remove(rider)
        return True

    def tick(self):
        """Advance the simulation by one tick.

        Charges operating costs for busy riders and moves every rider. Errors in
        one rider are logged and do not stop the others (error recovery).

        Returns:
            The new tick value.
        """
        globalvar.set_value("tick", self.tick_count + 1)
        busy = sum(1 for rider in self.riders if rider.state != IDLE)
        if busy:
            self.add_funds(-OPERATING_COST_PER_BUSY_TICK * busy)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive recovery
                logger.exception("Rider %s failed during tick; state reset",
                                 rider.rider_id)
                rider.state = IDLE
                rider.waypoints = []
                rider.target = None
        return self.tick_count

    def check_consistency(self):
        """Verify and repair internal state.

        Removes completed orders still referenced by riders and resets riders
        that are busy without any orders.

        Returns:
            List of human-readable messages describing repairs made.
        """
        issues = []
        for rider in self.riders:
            completed = [o for o in rider.orders if o.status == "completed"]
            if completed:
                rider.orders = [o for o in rider.orders if o.status != "completed"]
                issues.append(f"Removed {len(completed)} completed order(s) from rider {rider.rider_id}")
            if rider.state != IDLE and not rider.orders:
                rider.state = IDLE
                rider.waypoints = []
                rider.target = None
                issues.append(f"Reset rider {rider.rider_id} to idle (no orders)")
        return issues


def apply_config(config):
    """Override system parameters from a configuration dictionary.

    Recognised keys: ``initial_funds``, ``recruit_cost``, ``max_riders``,
    ``operating_cost_per_busy_tick``, ``delivery_fee``. Invalid values are
    ignored with a warning.

    Args:
        config: Dictionary, typically loaded from ``config.json``.
    """
    global RECRUIT_COST, MAX_RIDERS, OPERATING_COST_PER_BUSY_TICK
    mapping = {
        "initial_funds": ("initial_funds", globalvar),
        "recruit_cost": ("recruit_cost", None),
        "max_riders": ("max_riders", None),
        "operating_cost_per_busy_tick": ("operating_cost_per_busy_tick", None),
        "delivery_fee": ("delivery_fee", order_model),
    }
    for key, (_, target) in mapping.items():
        if key not in config:
            continue
        try:
            value = int(config[key])
        except (TypeError, ValueError):
            logger.warning("Ignoring invalid config value for %s: %r", key, config[key])
            continue
        if key == "initial_funds":
            globalvar.INITIAL_FUNDS = value
        elif key == "recruit_cost":
            RECRUIT_COST = value
        elif key == "max_riders":
            MAX_RIDERS = value
        elif key == "operating_cost_per_busy_tick":
            OPERATING_COST_PER_BUSY_TICK = value
        elif key == "delivery_fee":
            order_model.DELIVERY_FEE = value


def init_system():
    """Initialise global variables and create the system manager.

    Sets startup funds, an empty rider list, rider id counter 0, running state
    True, and tick 0. Stores the manager under the ``"system"`` key.
    """
    globalvar._init()
    manager = SystemManager()
    globalvar.set_value("system", manager)
    logger.info("System initialised with funds %s", manager.funds)
