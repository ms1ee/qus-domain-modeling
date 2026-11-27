"""Rider model: movement, state and orders."""

import globalvar
from path_planner import PathPlanner

IDLE = 0
PICKING_UP = 1
DELIVERING = 2


class RiderState:
    """Rider state enumeration."""
    IDLE = IDLE
    PICKING_UP = PICKING_UP
    DELIVERING = DELIVERING
    NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}


_planner = PathPlanner()


class Rider:
    """A delivery rider moving on the grid."""

    def __init__(self, rider_id, x=400, y=400, speed=20):
        self.rider_id = rider_id
        self.x = int(x)
        self.y = int(y)
        self.speed = int(speed)
        self.state = IDLE
        self.orders = []
        self.special_case = not _planner.is_on_street(self.x, self.y)
        self.log = []
        self.route_points = None
        self._route_target = None
        self._order_travel = 0
        self.total_distance = 0
        self._log("spawn", None)

    # ------------------------------------------------------------------ helpers
    def _log(self, event, order_id):
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": globalvar.get_value("tick", 0) or 0,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    @property
    def active_orders(self):
        return [o for o in self.orders if getattr(o, "status", None) != "completed"]

    @property
    def current_order(self):
        active = self.active_orders
        return active[0] if active else None

    @property
    def state_name(self):
        return RiderState.NAMES.get(self.state, str(self.state))

    def _accept_next(self):
        order = self.current_order
        if order is None:
            self.state = IDLE
            return False
        if order.status == "delivering":
            self.state = DELIVERING
        else:
            self.state = PICKING_UP
            order.status = "picking_up"
        if getattr(order, "rider_id", None) is None:
            order.rider_id = self.rider_id
        self.route_points = None
        self._order_travel = 0
        self._log("accepted_order", order.id)
        return True

    def _advance_towards(self, target, budget):
        if self.route_points is None or self._route_target != target:
            route = _planner.plan((self.x, self.y), target, self.speed)
            self.route_points = list(route.points[1:])
            self._route_target = target
        while budget > 0 and self.route_points:
            wx, wy = self.route_points[0]
            dx, dy = wx - self.x, wy - self.y
            if dx == 0 and dy == 0:
                self.route_points.pop(0)
                continue
            if dx != 0:
                step = min(abs(dx), budget)
                self.x += step if dx > 0 else -step
            else:
                step = min(abs(dy), budget)
                self.y += step if dy > 0 else -step
            budget -= step
            self._order_travel += step
            self.total_distance += step
            if (self.x, self.y) == (wx, wy):
                self.route_points.pop(0)
        self.special_case = not _planner.is_on_street(self.x, self.y)
        if not self.route_points and (self.x, self.y) != target:
            self.route_points = None
        return budget

    # ------------------------------------------------------------------ public
    def move(self):
        """Advance the rider by one tick (movement + state transitions)."""
        tick = globalvar.get_value("tick", 0) or 0
        budget = self.speed
        if self.state == IDLE:
            self._accept_next()
        guard = 0
        while self.state != IDLE and guard < 1000:
            guard += 1
            order = self.current_order
            if order is None:
                self.state = IDLE
                self.route_points = None
                break
            if self.state == PICKING_UP:
                target = (order.res_pos[0], order.res_pos[1])
            else:
                target = (order.cus_pos[0], order.cus_pos[1])
            if (self.x, self.y) != target:
                budget = self._advance_towards(target, budget)
            if (self.x, self.y) != target:
                break
            if self.state == PICKING_UP:
                self.state = DELIVERING
                order.status = "delivering"
                order.pickup_time = tick
                self.route_points = None
                self._log("arrived_at_merchant", order.id)
            else:
                order.status = "completed"
                order.completion_time = tick
                start = getattr(order, "start_time", None) or 0
                order.time_taken = tick - start
                order.distance = self._order_travel
                self.state = IDLE
                self.route_points = None
                self._log("delivered_to_customer", order.id)
                self._accept_next()

    def planned_route(self):
        """Route through all remaining targets of active orders."""
        dests = []
        for i, o in enumerate(self.active_orders):
            if not (i == 0 and self.state == DELIVERING):
                dests.append(tuple(o.res_pos))
            dests.append(tuple(o.cus_pos))
        return _planner.plan_multi((self.x, self.y), dests, self.speed)

    def to_dict(self):
        return {
            "rider_id": self.rider_id, "x": self.x, "y": self.y,
            "speed": self.speed, "state": self.state,
            "special_case": self.special_case,
            "orders": [o.id for o in self.orders], "log": self.log,
            "total_distance": self.total_distance,
        }

    def __repr__(self):
        return "Rider(id=%s, pos=(%d,%d), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state, len(self.orders))
