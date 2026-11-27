"""Display helpers."""
import globalvar
from path_planner import PathPlanner

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Render status and maps."""

    def render_map(self, route=None, orders=None):
        grid = [["." for _ in range(8)] for _ in range(8)]
        for px, py in self._cells(route or []):
            grid[py][px] = "#"
        for o in orders or []:
            grid[o.res_pos[1] // 100][o.res_pos[0] // 100] = "S"
            grid[o.cus_pos[1] // 100][o.cus_pos[0] // 100] = "C"
        for r in globalvar.get_value("riders", []):
            grid[min(r.y // 100, 7)][min(r.x // 100, 7)] = "R"
        return "\n".join(" ".join(row) for row in grid)

    @staticmethod
    def _cells(points):
        cells = set()
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            ax, ay, bx, by = ax // 100, ay // 100, bx // 100, by // 100
            for x in range(min(ax, bx), max(ax, bx) + 1):
                for y in range(min(ay, by), max(ay, by) + 1):
                    cells.add((x, y))
        if len(points) == 1:
            cells.add((points[0][0] // 100, points[0][1] // 100))
        return cells

    def status(self):
        riders = globalvar.get_value("riders", [])
        lines = ["Tick: %d  Funds: %d  Riders: %d" % (
            globalvar.get_value("tick", 0), globalvar.get_value("funds", 0), len(riders))]
        for r in riders:
            lines.append("Rider %d at (%d,%d) %s orders=%s" % (
                r.rider_id, r.x, r.y, STATES[r.state], [o.id for o in r.orders]))
        return "\n".join(lines)

    def orders(self):
        lines = []
        for o in globalvar.get_value("orders", []):
            took = (o.complete_time - o.create_time) if o.complete_time is not None else "-"
            lines.append("Order %d start=%d res=%s cus=%s dist=%d time=%s rider=%s status=%s" % (
                o.id, o.create_time, o.res_pos, o.cus_pos, o.distance, took,
                o.rider_id, o.status))
        return "\n".join(lines) or "No orders."

    def riders(self):
        lines = []
        for r in globalvar.get_value("riders", []):
            for e in r.log:
                lines.append("t=%s rider=%d %s order=%s at (%s,%s)" % (
                    e["time"], r.rider_id, e["event"], e["order_id"], e["x"], e["y"]))
        return "\n".join(lines) or "No riders."
