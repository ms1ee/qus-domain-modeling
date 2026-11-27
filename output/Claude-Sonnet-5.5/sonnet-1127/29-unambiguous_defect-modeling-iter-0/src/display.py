"""Display helpers."""
import globalvar

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Text rendering."""

    def status(self):
        lines = ["Funds: %s" % globalvar.get_value("funds"),
                 "Tick: %s" % globalvar.get_value("tick"),
                 "Riders: %d" % len(globalvar.get_value("riders"))]
        for r in globalvar.get_value("riders"):
            lines.append("  Rider %d at (%d,%d) %s orders=%s" % (
                r.rider_id, r.x, r.y, STATES[r.state],
                [o.id for o in r.orders]))
        return "\n".join(lines)

    def orders(self):
        orders = globalvar.get_value("orders")
        if not orders:
            return "No orders."
        return "\n".join(
            "Order %d start=%s rest=%s cust=%s dist=%d time=%s rider=%s %s" % (
                o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
                o.time_taken, o.rider_id, o.status) for o in orders)

    def riders_log(self):
        lines = []
        for r in globalvar.get_value("riders"):
            for e in r.log:
                lines.append("Rider %d t=%s (%s,%s) %s order=%s" % (
                    r.rider_id, e["time"], e["x"], e["y"], e["event"],
                    e["order_id"]))
        return "\n".join(lines) or "No records."

    def map(self, path=None, order=None):
        """ASCII 8x8 map; R rider, S restaurant, C customer, * route."""
        g = [["." for _ in range(8)] for _ in range(8)]
        if path:
            pts = path.waypoints
            for a, b in zip(pts, pts[1:]):
                n = max(abs(a[0] - b[0]), abs(a[1] - b[1])) // 50
                for i in range(n + 1):
                    x = a[0] + (b[0] - a[0]) * i // max(n, 1)
                    y = a[1] + (b[1] - a[1]) * i // max(n, 1)
                    g[min(7, y // 100)][min(7, x // 100)] = "*"
        if order:
            g[order.res_pos[1] // 100][order.res_pos[0] // 100] = "S"
            g[order.cus_pos[1] // 100][order.cus_pos[0] // 100] = "C"
        for r in globalvar.get_value("riders"):
            g[min(7, r.y // 100)][min(7, r.x // 100)] = "R"
        return "\n".join(" ".join(row) for row in reversed(g))
