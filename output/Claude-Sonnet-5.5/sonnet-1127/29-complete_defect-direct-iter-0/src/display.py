"""Display manager."""
from . import globalvar
from .pathplanner import PathPlanner

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Text rendering."""

    @staticmethod
    def render_map(route=None, orders=None, riders=None):
        """ASCII map; '#' streets between cells."""
        grid = [["." for _ in range(8)] for _ in range(8)]
        for p in route or []:
            grid[min(7, p[1] // 100)][min(7, p[0] // 100)] = "*"
        for o in orders or []:
            if o.status != "completed":
                grid[o.res_pos[1] // 100][o.res_pos[0] // 100] = "S"
                grid[o.cus_pos[1] // 100][o.cus_pos[0] // 100] = "C"
        for r in riders or []:
            grid[min(7, r.y // 100)][min(7, r.x // 100)] = "R"
        sep = "#" * 17
        lines = [sep]
        for row in grid:
            lines.append("#" + "#".join(row) + "#")
            lines.append(sep)
        return "\n".join(lines)

    @staticmethod
    def route_cells(start, end):
        """Cells traversed from start to end."""
        cells = []
        pos = tuple(start)
        cells.append(pos)
        while pos != tuple(end):
            pos = PathPlanner.step(pos, end, 50)
            cells.append(pos)
        return cells

    def status(self):
        riders = globalvar.get_value("riders")
        out = ["Time: %d  Funds: %d  Riders: %d" % (
            globalvar.get_value("time"), globalvar.get_value("funds"),
            len(riders))]
        for r in riders:
            out.append("  Rider %d at (%d,%d) speed %d %s orders=%s" % (
                r.rider_id, r.x, r.y, r.speed, STATES[r.state],
                [o.id for o in r.orders]))
        out.append(self.render_map(orders=globalvar.get_value("orders"),
                                   riders=riders))
        return "\n".join(out)

    def orders(self):
        orders = globalvar.get_value("orders")
        if not orders:
            return "No orders."
        out = []
        for o in orders:
            out.append("Order %d: start=%d restaurant=%s customer=%s "
                       "distance=%d time=%s rider=%s status=%s" % (
                           o.id, o.start_time, o.res_pos, o.cus_pos,
                           o.distance, o.duration, o.rider_id, o.status))
        return "\n".join(out)

    def riders(self):
        out = []
        for r in globalvar.get_value("riders"):
            for e in r.log:
                out.append("Rider %d t=%d %s order=%s at (%d,%d)" % (
                    r.rider_id, e["time"], e["event"], e["order_id"],
                    e["x"], e["y"]))
        return "\n".join(out) or "No riders."
