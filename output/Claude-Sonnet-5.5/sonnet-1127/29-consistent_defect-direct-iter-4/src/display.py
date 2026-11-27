"""Display helpers."""
import globalvar

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Status and map rendering."""

    def status(self):
        riders = globalvar.get_value("riders")
        lines = ["Time: %s  Funds: %s  Riders: %d" % (
            globalvar.get_value("time"), globalvar.get_value("funds"),
            len(riders))]
        for r in riders:
            lines.append("  Rider %d at (%d,%d) %s orders=%s" % (
                r.rider_id, r.x, r.y, STATES[r.state],
                [o.id for o in r.orders]))
        return "\n".join(lines)

    def orders(self):
        lines = []
        for o in globalvar.get_value("orders"):
            took = (o.end_time - o.start_time) if o.end_time is not None \
                else "-"
            lines.append("Order %d start=%s res=%s cus=%s dist=%d time=%s "
                         "rider=%s status=%s" % (
                             o.id, o.start_time, o.res_pos, o.cus_pos,
                             o.distance, took, o.rider_id, o.status))
        return "\n".join(lines) or "No orders."

    def riders_log(self):
        lines = []
        for r in globalvar.get_value("riders"):
            for e in r.log:
                lines.append("Rider %d t=%s %s at (%d,%d) order=%s" % (
                    r.rider_id, e["time"], e["event"], e["x"], e["y"],
                    e["order_id"]))
        return "\n".join(lines) or "No riders."

    def map(self, path=None):
        """16x16 ASCII map; each cell is 50 units."""
        g = [["#" if (i % 2 == 0 or j % 2 == 0) else "." for j in range(16)]
             for i in range(16)]

        def cell(x, y):
            return min(15, y // 50), min(15, x // 50)

        if path:
            for a, b in zip(path, path[1:]):
                (r1, c1), (r2, c2) = cell(*a), cell(*b)
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    for c in range(min(c1, c2), max(c1, c2) + 1):
                        g[r][c] = "*"
        for o in globalvar.get_value("orders"):
            if o.status != "completed":
                r, c = cell(*o.res_pos)
                g[r][c] = "S"
                r, c = cell(*o.cus_pos)
                g[r][c] = "C"
        for rd in globalvar.get_value("riders"):
            r, c = cell(rd.x, rd.y)
            g[r][c] = "R"
        return "\n".join("".join(row) for row in g)
