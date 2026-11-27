"""System initialisation and core resource management."""

import logging

try:
    from . import config, globalvar
    from .grid_map import GridMap
    from .path_planner import PathPlanner
    from .rider import Rider, RiderState
    from .order import OrderManager
except ImportError:  # pragma: no cover
    import config
    import globalvar
    from grid_map import GridMap
    from path_planner import PathPlanner
    from rider import Rider, RiderState
    from order import OrderManager

logger = logging.getLogger(__name__)


class SystemManager:
    """Manages funds, riders, simulated time and the running state."""

    def __init__(self, cfg=None):
        self.config = dict(config.DEFAULT_CONFIG)
        if cfg:
            self.config.update(cfg)
        self.recruitment_cost = int(self.config["recruitment_cost"])
        self.recruitment_threshold = int(self.config["recruitment_threshold"])
        self.grid_map = GridMap()
        self.planner = PathPlanner()
        self.order_manager = OrderManager(self, self.planner)
        self.last_recruited = None

    # global state accessors -----------------------------------------------
    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", value)

    @property
    def riders(self):
        r = globalvar.get_value("riders")
        if r is None:
            r = []
            globalvar.set_value("riders", r)
        return r

    @property
    def rider_id_counter(self):
        return globalvar.get_value("rider_id_counter", 0)

    @property
    def running(self):
        return bool(globalvar.get_value("running", False))

    @running.setter
    def running(self, value):
        globalvar.set_value("running", bool(value))
        globalvar.set_value("is_running", bool(value))

    @property
    def current_tick(self):
        return globalvar.get_value("time", 0)

    # riders -----------------------------------------------------------------
    def recruit_rider(self, force=False):
        """Recruit a new rider if funds allow (funds >= threshold)."""
        if not force and self.funds < self.recruitment_threshold:
            return None
        counter = self.rider_id_counter + 1
        globalvar.set_value("rider_id_counter", counter)
        globalvar.set_value("rider_id", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        self.funds = self.funds - self.recruitment_cost
        self.last_recruited = rider
        logger.info("Recruited rider %d, funds now %d", counter, self.funds)
        return rider

    def idle_riders(self):
        return [r for r in self.riders
                if int(r.state) == RiderState.IDLE and not r.active_orders()]

    def check_recruitment(self):
        """Recruit when funds >= threshold and pending > idle riders."""
        pending = len(self.order_manager.pending_orders())
        if self.funds >= self.recruitment_threshold and \
                pending > len(self.idle_riders()):
            return self.recruit_rider()
        return None

    # simulation -------------------------------------------------------------
    def tick(self, n=1):
        """Advance the simulation by ``n`` ticks."""
        for _ in range(max(0, int(n))):
            globalvar.set_value("time", self.current_tick + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception:  # pragma: no cover - recovery
                    logger.exception("Rider %s failed to move; resetting",
                                     rider.rider_id)
                    rider.route = []
        return self.current_tick

    def stop(self):
        self.running = False

    def check_consistency(self):
        """Return a list of detected consistency problems (and fix them)."""
        problems = []
        seen = set()
        for r in self.riders:
            if r.rider_id in seen:
                problems.append("duplicate rider id %s" % r.rider_id)
            seen.add(r.rider_id)
            if not r.active_orders() and int(r.state) != RiderState.IDLE:
                problems.append("rider %s busy without orders; reset"
                                % r.rider_id)
                r.state = RiderState.IDLE
                r.current_order = None
        return problems


_manager = None


def init_system(cfg=None):
    """Initialise all global system parameters and return the manager."""
    global _manager
    globalvar._init()
    manager = SystemManager(cfg)
    globalvar.set_value("config", manager.config)
    globalvar.set_value("funds", int(manager.config["initial_funds"]))
    globalvar.set_value("money", globalvar.get_value("funds"))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("rider_id", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("is_running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("grid_map", manager.grid_map)
    globalvar.set_value("system", manager)
    _manager = manager
    return manager


def get_system():
    """Return the active SystemManager, initialising if needed."""
    mgr = globalvar.get_value("system")
    if mgr is None:
        if globalvar.get_value("riders") is None:
            return init_system()
        mgr = SystemManager(globalvar.get_value("config"))
        globalvar.set_value("system", mgr)
        if globalvar.get_value("funds") is None:
            globalvar.set_value("funds", config.INITIAL_FUNDS)
    return mgr
