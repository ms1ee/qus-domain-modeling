"""Display manager."""
import globalvar
from path_planner import PathPlanner

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Status and map rendering."""

    @staticmethod
    def render_map(riders=(), orders=(), path=None):
        grid = [["." for _ in range(8)] for _ in range(8)]
        if path:
            for a, b in zip(path, path[1:]):
                n = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
                for i in range(n + 1):
                    x = a[0] + (b[0] - a[0]) * i // max(n, 1)
                    y = a[1] + (b[1] - a[1]) * i // max(n, 1)
                    grid[min(7, y // 100)][min(7, x // 100)] = "*"
        for o in orders:
            if o.status != "completed":
                grid[o.res_pos[1] // 100][o.res_pos[0] // 100] = "S"
                grid[o.cus_pos[1] // 100][o.cus_pos[0] // 100] = "C"
        for r in riders:
            grid[min(7, r.y // 100)][min(7, r.x // 100)] = "R"
        return "\n".join(" ".join(row) for row in grid)

    @staticmethod
    def status():
        riders = globalvar.get_value("riders", [])
        lines = ["Time: %s  Funds: %s  Riders: %d" % (
            globalvar.get_value("time"), globalvar.get_value("funds"),
            len(riders))]
        for r in riders:
            lines.append("Rider %d at (%d,%d) %s orders=%s" % (
                r.rider_id, r.x, r.y, STATES[r.state],
                [o.id for o in r.orders]))
        lines.append(DisplayManager.render_map(
            riders, globalvar.get_value("orders", [])))
        return "\n".join(lines)

    @staticmethod
    def orders():
        out = []
        for o in globalvar.get_value("orders", []):
            took = (o.end_time - o.start_time) if o.end_time is not None else "-"
            out.append("Order %d start=%s res=%s cus=%s dist=%d time=%s rider=%s [%s]"
                       % (o.id, o.start_time, o.res_pos, o.cus_pos,
                          o.distance, took, o.rider_id, o.status))
        return "\n".join(out) or "No orders."

    @staticmethod
    def riders():
        out = []
        for r in globalvar.get_value("riders", []):
            for e in r.log:
                out.append("t=%s rider %d %s order=%s at %s" % (
                    e["time"], r.rider_id, e["event"], e["order_id"], e["pos"]))
        return "\n".join(out) or "No riders."

    @staticmethod
    def route(order, rider):
        pts = [rider.pos, order.res_pos, order.cus_pos]
        path = PathPlanner.plan(pts[0], pts[1])[:-1] + PathPlanner.plan(pts[1], pts[2])
        total = PathPlanner.distance(pts[0], pts[1]) + order.distance
        eta = -(-total // rider.speed)
        return "%s\nSpeed %d, estimated time %d ticks" % (
            DisplayManager.render_map([rider], [order], path), rider.speed, eta)
