"""Display manager."""

import globalvar
from path_planner import PathPlanner

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Text rendering."""

    @staticmethod
    def status():
        """System status text."""
        riders = globalvar.get_value("riders")
        lines = ["Time: %d  Funds: %d  Riders: %d" % (
            globalvar.get_value("time"), globalvar.get_value("funds"),
            len(riders))]
        for r in riders:
            lines.append("  Rider %d at (%d,%d) %s orders=%s" % (
                r.rider_id, r.x, r.y, STATES[r.state],
                [o.id for o in r.orders]))
        return "\n".join(lines)

    @staticmethod
    def orders():
        """Order list text."""
        lines = []
        for o in globalvar.get_value("orders"):
            lines.append("Order %d start=%s res=%s cus=%s dist=%d took=%s "
                         "rider=%s status=%s" % (
                             o.id, o.start_time, o.res_pos, o.cus_pos,
                             o.distance, o.duration, o.rider_id, o.status))
        return "\n".join(lines) or "No orders."

    @staticmethod
    def riders_log():
        """Rider history text."""
        lines = []
        for r in globalvar.get_value("riders"):
            for e in r.log:
                lines.append("Rider %d t=%d %s at (%d,%d) order=%s" % (
                    r.rider_id, e["time"], e["event"], e["x"], e["y"],
                    e["order_id"]))
        return "\n".join(lines) or "No rider events."

    @staticmethod
    def map(route=None, order=None):
        """ASCII 8x8 map; '#' street, '.' empty, '*' route."""
        grid = [["." for _ in range(8)] for _ in range(8)]
        for c, r in PathPlanner.cells_on_path(route or []):
            grid[r][c] = "#"
        for o in globalvar.get_value("orders"):
            if o.status != "completed":
                grid[o.res_pos[1] // 100][o.res_pos[0] // 100] = "S"
                grid[o.cus_pos[1] // 100][o.cus_pos[0] // 100] = "C"
        for r in globalvar.get_value("riders"):
            grid[min(r.y // 100, 7)][min(r.x // 100, 7)] = "R"
        return "\n".join(" ".join(row) for row in grid)
