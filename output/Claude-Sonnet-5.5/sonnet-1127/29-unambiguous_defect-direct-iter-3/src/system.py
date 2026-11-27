"""System manager and initialization."""
import globalvar

RIDER_COST = 100


def init_system():
    """Initialize global state."""
    globalvar._init()
    globalvar.set_value("funds", 10000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_counter", 0)


class SystemManager:
    """Manages funds and riders."""

    @staticmethod
    def recruit():
        """Create a new rider if funds allow; return it or None."""
        from rider import Rider
        funds = globalvar.get_value("funds", 0)
        if funds < RIDER_COST:
            return None
        rid = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", rid)
        globalvar.set_value("funds", funds - RIDER_COST)
        r = Rider(rid)
        globalvar.get_value("riders").append(r)
        return r
