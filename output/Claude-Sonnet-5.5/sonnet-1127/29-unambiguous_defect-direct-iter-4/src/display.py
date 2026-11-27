"""Display."""
import globalvar
from path_planner import PathPlanner

STATE = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Status and map display."""

    def map(self, route=None, riders=True):
        n = 17
        g = [["+" if (i % 2 == 0 and j % 2 == 0) else
              ("." if (i % 2 == 0 or j % 2 == 0) else " ")
              for j in range(n)] for i in range(n)]
        if route:
            for a, b in zip(route, route[1:]):
                for t in range(0, 101):
                    x = a[0] + (b[0] - a[0]) * t // 100
                    y = a[1] + (b[1] - a[1]) * t // 100
                    g[min(y // 50, 16)][min(x // 50, 16)] = "*"
            g[route[-1][1] // 50][route[-1][0] // 50] = "C"
            if len(route) > 2:
                pass
        for o in globalvar.get_value("orders"):
            if o.status != "completed":
                g[o.res_pos[1] // 50][o.res_pos[0] // 50] = "R"
                g[o.cus_pos[1] // 50][o.cus_pos[0] // 50] = "C"
        if riders:
            for r in globalvar.get_value("riders"):
                g[min(r.y // 50, 16)][min(r.x // 50, 16)] = "B"
        return "\n".join(" ".join(row) for row in g)

    def status(self):
        rs = globalvar.get_value("riders")
        lines = ["Time: %d  Funds: %d  Riders: %d" % (
            globalvar.get_value("time"), globalvar.get_value("funds"),
            len(rs))]
        for r in rs:
            lines.append("Rider %d at (%d,%d) %s orders=%s" % (
                r.rider_id, r.x, r.y, STATE[r.state],
                [o.id for o in r.orders]))
        return "\n".join(lines)

    def orders(self):
        os_ = globalvar.get_value("orders")
        if not os_:
            return "No orders."
        lines = []
        for o in os_:
            lines.append(
                "Order %d start=%d res=%s cus=%s dist=%d time=%s rider=%s [%s]"
                % (o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
                   o.duration if o.duration is not None else "-",
                   o.rider_id, o.status))
        return "\n".join(lines)

    def riders_log(self):
        lines = []
        for r in globalvar.get_value("riders"):
            for e in r.log:
                lines.append("t=%s rider=%d %s order=%s at (%d,%d)" % (
                    e["time"], r.rider_id, e["event"], e["order_id"],
                    e["x"], e["y"]))
        return "\n".join(lines) or "No records."
