"""Display manager."""
import globalvar

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Status display and ASCII map."""

    def status(self):
        riders = globalvar.get_value("riders")
        lines = ["Funds: %d" % globalvar.get_value("funds"),
                 "Time: %d" % globalvar.get_value("time"),
                 "Riders: %d" % len(riders)]
        for r in riders:
            lines.append("  Rider %d at (%d,%d) %s, orders: %s" % (
                r.rider_id, r.x, r.y, STATES[r.state],
                [(o.id, o.status) for o in r.orders]))
        return "\n".join(lines)

    def orders(self):
        lines = []
        for o in globalvar.get_value("orders"):
            t = (o.end_time - o.start_time) if o.end_time is not None else "-"
            lines.append("Order %d start=%d res=%s cus=%s dist=%d time=%s "
                         "rider=%s status=%s" % (
                             o.id, o.start_time, o.res_pos, o.cus_pos,
                             o.distance, t, o.rider_id, o.status))
        return "\n".join(lines) or "No orders."

    def riders_log(self):
        lines = []
        for r in globalvar.get_value("riders"):
            for e in r.log:
                lines.append("Rider %d t=%d pos=%s %s order=%s" % (
                    r.rider_id, e["time"], e["pos"], e["event"],
                    e["order_id"]))
        return "\n".join(lines) or "No riders."

    def map(self, path=None, riders=None, orders=None):
        """16x16 ASCII map; each cell is 50 units."""
        n = 16
        g = [["." for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i % 2 == 0 or j % 2 == 0:
                    g[i][j] = "#"
        def cell(x, y):
            return min(n - 1, y // 50), min(n - 1, x // 50)
        if path:
            for a, b in zip(path, path[1:]):
                for t in range(0, 101, 10):
                    x = a[0] + (b[0] - a[0]) * t // 100
                    y = a[1] + (b[1] - a[1]) * t // 100
                    i, j = cell(x, y)
                    g[i][j] = "*"
        for o in orders or globalvar.get_value("orders"):
            if o.status == "completed":
                continue
            i, j = cell(*o.res_pos)
            g[i][j] = "S"
            i, j = cell(*o.cus_pos)
            g[i][j] = "C"
        for r in riders if riders is not None else globalvar.get_value("riders"):
            i, j = cell(r.x, r.y)
            g[i][j] = "R"
        return "\n".join("".join(row) for row in g)
