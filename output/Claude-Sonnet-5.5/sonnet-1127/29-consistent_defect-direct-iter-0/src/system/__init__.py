"""System initialization and management."""
import globalvar


def init_system():
    """Initialize global state."""
    globalvar._init()
    globalvar.set_value("funds", 1000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_counter", 0)


class SystemManager:
    """Manage funds, riders and system state."""

    def recruit_if_needed(self, force=False):
        """Recruit a rider when conditions are met. Returns new rider or None."""
        from rider import Rider
        funds = globalvar.get_value("funds")
        riders = globalvar.get_value("riders")
        pending = sum(1 for o in globalvar.get_value("orders")
                      if o.status != "completed")
        idle = sum(1 for r in riders if r.state == 0)
        if force or (funds >= 300 and pending > idle):
            rid = globalvar.get_value("rider_id_counter") + 1
            globalvar.set_value("rider_id_counter", rid)
            r = Rider(rid)
            riders.append(r)
            globalvar.set_value("funds", funds - 500)
            return r
        return None
