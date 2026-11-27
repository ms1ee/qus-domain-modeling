"""Display manager."""
import globalvar
from pathplanner import PathPlanner


class DisplayManager:
    """Status and map rendering."""

    @staticmethod
    def status():
        lines = ["Time: %d  Funds: %d  Riders: %d" % (
            globalvar.get_value("time"), globalvar.get_value("funds"),
            len(globalvar.get_value("riders")))]
        names = {0: "idle", 1: "picking up", 2: "delivering"}
        for r in globalvar.get_value("riders"):
            lines.append("Rider %d at (%d,%d) %s, orders: %s" % (
                r.rider_id, r.x, r.y, names[r.state],
                [o.id for o in r.orders]))
        return "\n".join(lines)

    @staticmethod
    def orders():
        os_ = globalvar.get_value("orders")
        if not os_:
            return "No orders."
        out = []
        for o in os_:
            took = (o.end_time - o.start_time) if o.end_time is not None \
                else "-"
            out.append("Order %d start=%d res=%s cus=%s dist=%.1f "
                       "time=%s rider=%s status=%s" % (
                           o.id, o.start_time, o.res_pos, o.cus_pos,
                           o.distance, took, o.rider_id, o.status))
        return "\n".join(out)

    @staticmethod
    def riders_log():
        out = []
        for r in globalvar.get_value("riders"):
            for e in r.log:
                out.append("t=%d rider=%d %s order=%s at (%d,%d)" % (
                    e["time"], r.rider_id, e["event"], e["order_id"],
                    e["x"], e["y"]))
        return "\n".join(out) if out else "No records."

    @staticmethod
    def map(route=None):
        """Render 8x8 map; each cell 1 char, streets between."""
        size = 17
        g = [["#" if (i % 2 == 0 or j % 2 == 0) else "." for j in range(size)]
             for i in range(size)]

        def cell(p):
            return (min(p[1] // 100, 7) * 2 + 1, min(p[0] // 100, 7) * 2 + 1)

        def street(p):
            return (min(round(p[1] / 50), 16), min(round(p[0] / 50), 16))
        if route:
            for p in route:
                i, j = street(p)
                g[i][j] = "*"
        for o in globalvar.get_value("orders"):
            if o.status != "completed":
                i, j = cell(o.res_pos)
                g[i][j] = "S"
                i, j = cell(o.cus_pos)
                g[i][j] = "C"
        for r in globalvar.get_value("riders"):
            i, j = street((r.x, r.y))
            g[i][j] = "R"
        return "\n".join("".join(row) for row in g)

    @staticmethod
    def route_for(rider, order):
        pts = PathPlanner.route(rider.x, rider.y, *order.res_pos, rider.speed)
        pts += PathPlanner.route(*order.res_pos, *order.cus_pos,
                                 rider.speed)[1:]
        return pts
