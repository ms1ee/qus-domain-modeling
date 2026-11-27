"""System management."""
import globalvar
from rider import Rider


def init_system():
    """Initialise global state."""
    globalvar._init()
    globalvar.set_value("funds", 1000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])


class SystemManager:
    """Funds, riders and recruitment."""

    @staticmethod
    def pending_count():
        return sum(1 for o in globalvar.get_value("orders", [])
                   if o.status == "pending")

    @staticmethod
    def maybe_recruit(extra_pending=0):
        """Hire a rider if conditions are met. Return True if hired."""
        riders = globalvar.get_value("riders")
        idle = sum(1 for r in riders if r.state == 0 and not r.pending_orders())
        pending = SystemManager.pending_count() + extra_pending
        if globalvar.get_value("funds") >= 300 and pending > idle:
            n = globalvar.get_value("rider_id_counter") + 1
            globalvar.set_value("rider_id_counter", n)
            riders.append(Rider(n))
            globalvar.set_value("funds", globalvar.get_value("funds") - 500)
            return True
        return False

    @staticmethod
    def tick():
        globalvar.set_value("time", globalvar.get_value("time") + 1)
        for r in globalvar.get_value("riders"):
            r.move()
