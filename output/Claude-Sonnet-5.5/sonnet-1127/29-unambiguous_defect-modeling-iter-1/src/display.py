"""Display manager."""
import globalvar
from grid_map import cell_of

STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Textual output."""

    def status(self):
        riders = globalvar.get_value("riders") or []
        lines = ["Tick: %s  Funds: %s  Riders: %d" % (
            globalvar.get_value("tick"), globalvar.get_value("funds"),
            len(riders))]
        for r in riders:
            lines.append("  Rider %d at (%d,%d) %s speed=%d orders=%s" % (
                r.rider_id, r.x, r.y, STATE_NAMES[r.state], r.speed,
                [o.id for o in r.orders]))
        lines.append(self.map())
        return "\n".join(lines)

    def orders(self):
        orders = globalvar.get_value("orders") or []
        if not orders:
            return "No orders."
        return "\n".join(
            "Order %d start=%s rest=%s cust=%s dist=%d time=%s rider=%s %s"
            % (o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
               o.time_taken, o.rider_id, o.status) for o in orders)

    def riders(self):
        out = []
        for r in globalvar.get_value("riders") or []:
            for e in r.log:
                out.append("t=%d rider %d %s order=%s at (%d,%d)" % (
                    e["time"], r.rider_id, e["event"], e["order_id"],
                    e["x"], e["y"]))
        return "\n".join(out) or "No records."

    def map(self, path=None):
        """ASCII 8x8 map: R rider, S restaurant, C customer, * route."""
        g = [["." for _ in range(8)] for _ in range(8)]
        if path:
            pts = path.waypoints
            for a, b in zip(pts, pts[1:]):
                n = max(abs(a[0] - b[0]), abs(a[1] - b[1])) // 10 + 1
                for i in range(n + 1):
                    x = a[0] + (b[0] - a[0]) * i // n
                    y = a[1] + (b[1] - a[1]) * i // n
                    g[cell_of(y)][cell_of(x)] = "*"
        for o in globalvar.get_value("orders") or []:
            if o.status != "completed":
                g[cell_of(o.res_pos[1])][cell_of(o.res_pos[0])] = "S"
                g[cell_of(o.cus_pos[1])][cell_of(o.cus_pos[0])] = "C"
        for r in globalvar.get_value("riders") or []:
            g[cell_of(r.y)][cell_of(r.x)] = "R"
        return "\n".join(" ".join(row) for row in reversed(g))
