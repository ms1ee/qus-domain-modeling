"""System initialisation and the core SystemManager."""

import json
import logging
import os

import globalvar
from gridmap import GridMap
from rider import Rider, RiderState

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "recruitment_cost": 300,
    "rider_speed": 10,
    "spawn_x": 435,
    "spawn_y": 385,
}


def load_config(path):
    """Load a JSON configuration file merged with defaults."""
    config = dict(DEFAULT_CONFIG)
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for key in DEFAULT_CONFIG:
                    if key in data:
                        config[key] = int(data[key])
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("Could not load config %s: %s", path, exc)
    return config


def init_system(config=None):
    """Initialise all global system parameters.

    Funds 1000, empty rider list, rider ID counter 0, running True, tick 0.
    Returns a :class:`SystemManager`.
    """
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    globalvar._init()
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", int(cfg["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)
    return SystemManager()


class SystemManager:
    """Manages funds, riders, simulated time and the running state."""

    def __init__(self):
        from order import OrderManager
        if not globalvar.has_value("riders"):
            globalvar.set_value("riders", [])
        self.grid = GridMap()
        self.order_manager = OrderManager(self)

    # --------------------------------------------------------- properties
    @property
    def config(self):
        return globalvar.get_value("config") or dict(DEFAULT_CONFIG)

    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", int(value))

    @property
    def riders(self):
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def rider_id_counter(self):
        return globalvar.get_value("rider_id_counter", 0)

    @property
    def running(self):
        return bool(globalvar.get_value("running", False))

    @running.setter
    def running(self, value):
        globalvar.set_value("running", bool(value))

    @property
    def current_tick(self):
        return globalvar.get_value("tick", 0)

    @property
    def recruitment_cost(self):
        return int(self.config.get("recruitment_cost", 300))

    # ------------------------------------------------------------ riders
    def idle_riders(self):
        """Riders that are idle and have no assigned orders."""
        return [r for r in self.riders if r.is_idle()]

    def recruit_rider(self):
        """Recruit a rider if funds allow. Returns the rider or None."""
        cost = self.recruitment_cost
        if self.funds < cost:
            return None
        self.funds = self.funds - cost
        counter = self.rider_id_counter + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        logger.info("Recruited rider %s (funds now %s)", counter, self.funds)
        return rider

    def check_recruitment(self):
        """Recruit riders while funds >= cost and pending > idle riders."""
        recruited = []
        pending = len(self.order_manager.pending_orders())
        idle = len(self.idle_riders())
        while self.funds >= self.recruitment_cost and pending > idle:
            rider = self.recruit_rider()
            if rider is None:
                break
            recruited.append(rider)
            idle += 1
        return recruited

    # -------------------------------------------------------------- time
    def advance_tick(self, n=1):
        """Advance the simulation by ``n`` ticks."""
        for _ in range(max(0, int(n))):
            globalvar.set_value("tick", self.current_tick + 1)
            try:
                self.order_manager.dispatch_pending()
            except Exception:  # pragma: no cover - defensive
                logger.exception("Dispatching pending orders failed")
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception:
                    logger.exception("Rider %s failed to move; recovering", rider.rider_id)
                    rider.reset_route()
            self.consistency_check()

    def consistency_check(self):
        """Check and repair system state. Returns a list of fixed issues."""
        issues = []
        for rider in self.riders:
            done = [o for o in rider.orders if o.is_completed()]
            for o in done:
                rider.orders.remove(o)
                issues.append("Removed completed order {} from rider {}".format(o.id, rider.rider_id))
            if not rider.orders and rider.state != RiderState.IDLE:
                rider.state = RiderState.IDLE
                rider.reset_route()
                issues.append("Rider {} reset to idle".format(rider.rider_id))
            rider.x = max(0, min(self.grid.map_size, rider.x))
            rider.y = max(0, min(self.grid.map_size, rider.y))
        for issue in issues:
            logger.warning(issue)
        return issues

    def stop(self):
        """Stop the main loop."""
        self.running = False
