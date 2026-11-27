"""Display helpers."""
import globalvar
from path_planner import PathPlanner

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Status and map rendering."""

    @staticmethod
    def map_text(path_pts=None, extra=None):
        grid = [["#" if (x + y) % 2 == 0 else "." for x in range(8)]
                for y in range(8)]
        if path_pts:
            for cx, cy in PathPlanner.cells(path_pts):
                grid[cy][cx] = "*"
        for o in globalvar.get_value("orders"):
            if o.status != "completed":
                rx, ry = o.res_pos
                cx, cy = o.cus_pos
                grid[ry // 100][rx // 100] = "S"
                grid[cy // 100][cx // 100] = "C"
        for r in globalvar.get_value("riders"):
            grid[min(r.y // 100, 7)][min(r.x // 100, 7)] = "R"
        return "\n".join(" ".join(row) for row in grid)

    @staticmethod
    def status_text():
        lines = ["Time: %s  Funds: %s  Riders: %d" % (
            globalvar.get_value("time"), globalvar.get_value("funds"),
            len(globalvar.get_value("riders")))]
        for r in globalvar.get_value("riders"):
            lines.append("  Rider %d at (%d,%d) %s orders=%s" % (
                r.rider_id, r.x, r.y, STATES[r.state],
                [o.id for o in r.orders]))
        return "\n".join(lines)

    @staticmethod
    def orders_text():
        os_ = globalvar.get_value("orders")
        if not os_:
            return "No orders."
        return "\n".join(
            "Order %d: start=%s res=%s cus=%s dist=%d time=%s rider=%s [%s]" % (
                o.id, o.create_time, o.res_pos, o.cus_pos, o.distance,
                o.duration, o.rider_id, o.status) for o in os_)

    @staticmethod
    def riders_text():
        lines = []
        for r in globalvar.get_value("riders"):
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%s (%s,%s) %s order=%s" % (
                    e["time"], e["x"], e["y"], e["event"], e["order_id"]))
        return "\n".join(lines) or "No riders."
