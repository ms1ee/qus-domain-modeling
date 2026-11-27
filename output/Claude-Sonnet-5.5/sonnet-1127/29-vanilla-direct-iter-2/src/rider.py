"""Rider model."""
import math
import globalvar


def _route(x, y, tx, ty):
    """Waypoints along streets from (x, y) to (tx, ty)."""
    pts = []
    cx, cy = x, y
    on_v = cx % 100 == 0
    on_h = cy % 100 == 0
    if not on_v and not on_h:
        # go to nearest horizontal street
        ny = round(cy / 100) * 100
        ny = min(max(ny, 0), 800)
        pts.append((cx, ny))
        cy = ny
    if cy % 100 == 0 and cx % 100 != 0:
        # on horizontal street: move horizontally to target column street
        nx = (tx // 100) * 100 if tx % 100 else tx
        # choose the street next to target
        nx = round(tx / 100) * 100
        pts.append((nx, cy))
        cx = nx
    # now on vertical street: move vertically to target row
    pts.append((cx, ty))
    cy = ty
    pts.append((tx, ty))
    return pts


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 435
        self.y = 385
        self.speed = 10
        self.state = 0
        self.orders = []
        self.special_case = False
        self.current = None
        self.path = []
        self.log = []
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("time", 0),
                         "x": self.x, "y": self.y})

    def _set_target(self, tx, ty):
        self.path = _route(self.x, self.y, tx, ty)

    def _advance(self):
        """Move up to speed units along path. Return True if path done."""
        budget = self.speed
        while self.path and budget > 0:
            px, py = self.path[0]
            d = math.hypot(px - self.x, py - self.y)
            if d <= budget:
                self.x, self.y = px, py
                budget -= d
                self.path.pop(0)
            else:
                self.x += round((px - self.x) / d * budget)
                self.y += round((py - self.y) / d * budget)
                budget = 0
        return not self.path

    def move(self):
        """Advance one tick."""
        if self.state == 0:
            if not self.orders:
                return
            self.current = self.orders[0]
            self.state = 1
            self._log("accepted_order", self.current.id)
            self._set_target(*self.current.res_pos)
        if self.state == 1:
            if self._advance():
                self.state = 2
                self._log("arrived_at_merchant", self.current.id)
                self._set_target(*self.current.cus_pos)
            return
        if self.state == 2:
            if self._advance():
                o = self.current
                self._log("delivered_to_customer", o.id)
                o.status = "completed"
                o.finish_time = globalvar.get_value("time", 0)
                if o in self.orders:
                    self.orders.remove(o)
                self.current = None
                self.state = 0
