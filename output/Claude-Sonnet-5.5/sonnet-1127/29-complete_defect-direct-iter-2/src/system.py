"""System management."""
import globalvar
from rider import Rider

RIDER_COST = 300


def init_system():
    """Initialize global state."""
    globalvar._init()
    globalvar.set_value("funds", 300)


class SystemManager:
    """Manage funds, riders and ticks."""

    def recruit(self):
        """Recruit a rider if funds suffice; return the rider or None."""
        funds = globalvar.get_value("funds", 0)
        if funds < RIDER_COST:
            return None
        globalvar.set_value("funds", funds - RIDER_COST)
        rid = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", rid)
        r = Rider(rid)
        globalvar.get_value("riders").append(r)
        return r

    def tick(self):
        """Advance simulation one tick."""
        globalvar.set_value("tick", globalvar.get_value("tick", 0) + 1)
        for r in globalvar.get_value("riders"):
            before = len(r.orders)
            r.move()
            if len(r.orders) < before:
                globalvar.set_value("funds", globalvar.get_value("funds") + 100)
