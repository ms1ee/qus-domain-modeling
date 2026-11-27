"""Display manager."""
import globalvar
from path_planner import PathPlanner

NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Status and ASCII map rendering."""

    @staticmethod
    def render_map(riders=(), orders=(), route=None):
        grid = [["." for _ in range(8)] for _ in range(8)]
        if route:
            for (a, b) in zip(route, route[1:]):
                n = max(abs(a[0] - b[0]), abs(a[1] - b[1])) // 50 + 1
                for i in range(n + 1):
                    x = a[0] + (b[0] - a[0]) * i // max(n, 1)
                    y = a[1] + (b[1] - a[1]) * i // max(n, 1)
                    grid[min(y // 100, 7)][min(x // 100, 7)] = "#"
        for o in orders:
            if o.status != "completed":
                gx, gy = o.res_pos[0] // 100, o.res_pos[1] // 100
                grid[gy][gx] = "S"
                gx, gy = o.cus_pos[0] // 100, o.cus_pos[1] // 100
                grid[gy][gx] = "C"
        for r in riders:
            grid[min(r.y // 100, 7)][min(r.x // 100, 7)] = "R"
        lines = []
        for row in range(7, -1, -1):
            lines.append(" ".join(grid[row]))
        return "\n".join(lines)

    @staticmethod
    def status():
        riders = globalvar.get_value("riders", [])
        out = ["Time: %s  Funds: %s  Riders: %d" % (
            globalvar.get_value("time"), globalvar.get_value("funds"),
            len(riders))]
        for r in riders:
            out.append("Rider %d at (%d,%d) speed %d %s orders=%s" % (
                r.rider_id, r.x, r.y, r.speed, NAMES[r.state],
                [o.id for o in r.orders]))
        out.append(DisplayManager.render_map(
            riders, globalvar.get_value("orders", [])))
        return "\n".join(out)

    @staticmethod
    def orders():
        orders = globalvar.get_value("orders", [])
        if not orders:
            return "No orders."
        out = []
        for o in orders:
            out.append("Order %d start=%s rest=%s cust=%s dist=%d time=%s "
                       "rider=%s status=%s" % (
                           o.id, o.start_time, o.res_pos, o.cus_pos,
                           o.distance, o.time_taken, o.rider_id, o.status))
        return "\n".join(out)

    @staticmethod
    def riders_log():
        out = []
        for r in globalvar.get_value("riders", []):
            for e in r.log:
                out.append("t=%s rider %d %s order=%s at (%s,%s)" % (
                    e["time"], r.rider_id, e["event"], e["order_id"],
                    e["x"], e["y"]))
        return "\n".join(out) or "No rider records."
