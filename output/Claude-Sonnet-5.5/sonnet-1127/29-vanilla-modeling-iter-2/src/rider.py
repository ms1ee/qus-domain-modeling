"""Rider model."""
import globalvar


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
        self.log = []
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("tick", 0),
                         "x": self.x, "y": self.y})

    @staticmethod
    def _nearest_street(v):
        return int(round(v / 100.0)) * 100

    def _step_toward(self, tx, ty):
        """Move up to speed units toward target, preferring streets."""
        budget = self.speed
        on_h = self.y % 100 == 0
        on_v = self.x % 100 == 0
        while budget > 0 and (self.x, self.y) != (tx, ty):
            if not on_h and not on_v:
                # get onto the nearest street (vertical line x multiple of 100)
                sx = self._nearest_street(self.x)
                if self.x == tx or abs(self.x - sx) == 0:
                    on_v = True
                    continue
                d = sx - self.x
                m = min(budget, abs(d))
                self.x += m if d > 0 else -m
                budget -= m
                on_v = self.x % 100 == 0
                continue
            if self.y != ty and (on_v and (self.x % 100 == 0)) and \
                    (self.x != tx or True):
                if self.x == tx or self.y % 100 != 0 or True:
                    # travel vertically along the street
                    if self.y != ty and not (self.y % 100 == 0 and
                                             self.x != tx and
                                             self.x % 100 != 0):
                        d = ty - self.y
                        m = min(budget, abs(d))
                        self.y += m if d > 0 else -m
                        budget -= m
                        on_h = self.y % 100 == 0
                        if budget == 0:
                            break
                        continue
            if self.x != tx:
                d = tx - self.x
                m = min(budget, abs(d))
                self.x += m if d > 0 else -m
                budget -= m
                on_v = self.x % 100 == 0
                on_h = self.y % 100 == 0
                continue
            break

    def move(self):
        """Advance one tick."""
        if self.state == 0 and self.orders:
            self.state = 1
            self._log("accepted_order", self.orders[0].id)
        if self.state == 0:
            return
        order = self.orders[0]
        if self.state == 1:
            tx, ty = order.res_pos
            if (self.x, self.y) != (tx, ty):
                self._step_toward(tx, ty)
            if (self.x, self.y) == (tx, ty):
                self.state = 2
                order.status = "picked"
                self._log("arrived_at_merchant", order.id)
            return
        tx, ty = order.cus_pos
        if (self.x, self.y) != (tx, ty):
            self._step_toward(tx, ty)
        if (self.x, self.y) == (tx, ty):
            order.status = "completed"
            order.completion_time = globalvar.get_value("tick", 0)
            self.orders.pop(0)
            self.state = 0
            self._log("delivered_to_customer", order.id)
