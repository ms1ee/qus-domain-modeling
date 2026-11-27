"""Display manager."""
import globalvar
from pathplanner import PathPlanner

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """ASCII output."""

    def map_text(self, riders=None, orders=None, route=None):
        """Draw 8x8 map: R rider, S restaurant, C customer, * route, . empty."""
        g = [["." for _ in range(8)] for _ in range(8)]
        for p in (route or []):
            pass
        if route:
            for a, b in zip(route, route[1:]):
                n = max(abs(a[0] - b[0]), abs(a[1] - b[1])) // 10 + 1
                for i in range(n + 1):
                    x = a[0] + (b[0] - a[0]) * i // n
                    y = a[1] + (b[1] - a[1]) * i // n
                    g[min(7, y // 100)][min(7, x // 100)] = "*"
        for o in orders or []:
            if o.status != "completed":
                g[o.res_pos[1] // 100][o.res_pos[0] // 100] = "S"
                g[o.cus_pos[1] // 100][o.cus_pos[0] // 100] = "C"
        for r in riders or []:
            g[min(7, r.y // 100)][min(7, r.x // 100)] = "R"
        return "\n".join(" ".join(row) for row in reversed(g))

    def status(self):
        """Status snapshot text."""
        riders = globalvar.get_value("riders")
        lines = ["Tick: %d  Funds: %d  Riders: %d" % (
            globalvar.get_value("tick"), globalvar.get_value("funds"),
            len(riders))]
        for r in riders:
            lines.append("Rider %d at (%d,%d) %s orders=%s" % (
                r.rider_id, r.x, r.y, STATES[r.state],
                [o.id for o in r.orders]))
        lines.append(self.map_text(riders, globalvar.get_value("orders")))
        return "\n".join(lines)

    def orders(self):
        """Order details text."""
        out = []
        for o in globalvar.get_value("orders"):
            out.append("Order %d start=%d rest=%s cust=%s dist=%d time=%s "
                       "rider=%s status=%s" % (
                           o.id, o.start_time, o.res_pos, o.cus_pos,
                           o.distance, o.time_taken, o.rider_id, o.status))
        return "\n".join(out) or "No orders."

    def riders_log(self):
        """Rider history text."""
        out = []
        for r in globalvar.get_value("riders"):
            for e in r.log:
                out.append("Rider %d t=%d (%d,%d) %s order=%s" % (
                    r.rider_id, e["time"], e["x"], e["y"], e["event"],
                    e["order_id"]))
        return "\n".join(out) or "No riders."

    def route(self, rider, order, planner=None):
        """Route description for an assigned rider."""
        planner = planner or PathPlanner()
        pts = planner.plan((rider.x, rider.y), order.res_pos, order.cus_pos)
        length = planner.length(pts)
        t = -(-length // rider.speed)
        return "Route speed=%d length=%d time=%d ticks\n%s" % (
            rider.speed, length, t,
            self.map_text([rider], [order], pts))
