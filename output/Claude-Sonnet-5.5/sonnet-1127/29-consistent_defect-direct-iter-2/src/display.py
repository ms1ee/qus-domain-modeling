"""Display."""
import globalvar
from path_planner import PathPlanner

STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Status and map rendering."""

    @staticmethod
    def map_text(riders=(), orders=(), route=None):
        n = 16
        g = [["." for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i % 2 == 0 or j % 2 == 0:
                    g[i][j] = "#"

        def cell(p):
            return min(n - 1, p[1] // 50), min(n - 1, p[0] // 50)

        if route:
            for a, b in zip(route, route[1:]):
                steps = max(abs(b[0] - a[0]), abs(b[1] - a[1])) // 50
                for s in range(steps + 1):
                    x = a[0] + (b[0] - a[0]) * s // max(steps, 1)
                    y = a[1] + (b[1] - a[1]) * s // max(steps, 1)
                    i, j = cell((x, y))
                    g[i][j] = "*"
        for o in orders:
            i, j = cell(o.res_pos)
            g[i][j] = "S"
            i, j = cell(o.cus_pos)
            g[i][j] = "C"
        for r in riders:
            i, j = cell((r.x, r.y))
            g[i][j] = "R"
        return "\n".join("".join(row) for row in g)

    @staticmethod
    def status_text():
        out = ["Funds: %d" % globalvar.get_value("funds"),
               "Time: %d" % globalvar.get_value("time"),
               "Riders: %d" % len(globalvar.get_value("riders"))]
        for r in globalvar.get_value("riders"):
            out.append("  Rider %d at (%d,%d) %s, orders: %s" % (
                r.rider_id, r.x, r.y, STATE_NAMES[r.state],
                [(o.id, o.status) for o in r.orders]))
        return "\n".join(out)

    @staticmethod
    def orders_text():
        out = []
        for o in globalvar.get_value("orders"):
            t = (o.end_time - o.start_time) if o.end_time is not None else "-"
            out.append("Order %d start=%s from=%s to=%s dist=%d time=%s rider=%s [%s]"
                       % (o.id, o.start_time, o.res_pos, o.cus_pos,
                          o.distance, t, o.rider_id, o.status))
        return "\n".join(out) or "No orders."

    @staticmethod
    def riders_text():
        out = []
        for r in globalvar.get_value("riders"):
            out.append("Rider %d:" % r.rider_id)
            for e in r.log:
                out.append("  t=%s %s order=%s pos=%s" % (
                    e["time"], e["event"], e["order_id"], e["pos"]))
        return "\n".join(out) or "No riders."
