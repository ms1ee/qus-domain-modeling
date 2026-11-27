"""System initialization and management."""
import globalvar


def init_system():
    """Initialize core parameters."""
    globalvar._init()
    globalvar.set_value("funds", 1000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])


class SystemManager:
    """Manage funds, riders and time."""

    @staticmethod
    def recruit_if_needed():
        """Recruit a rider if conditions hold. Returns True if added."""
        from rider import Rider
        orders = globalvar.get_value("orders", [])
        riders = globalvar.get_value("riders", [])
        pending = sum(1 for o in orders if o.status == "pending")
        idle = sum(1 for r in riders if r.state == 0 and not r.orders)
        if globalvar.get_value("funds", 0) >= 300 and pending > idle:
            rid = globalvar.get_value("rider_id_counter", 0) + 1
            globalvar.set_value("rider_id_counter", rid)
            globalvar.set_value("funds", globalvar.get_value("funds") - 300)
            riders.append(Rider(rid))
            return True
        return False

    @staticmethod
    def tick():
        """Advance one time unit."""
        globalvar.set_value("time", globalvar.get_value("time", 0) + 1)
        for r in globalvar.get_value("riders", []):
            r.move()
