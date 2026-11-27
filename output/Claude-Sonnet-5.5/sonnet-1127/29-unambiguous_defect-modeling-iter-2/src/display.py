"""Display manager."""
import globalvar
from pathplanner import PathPlanner, to_cell

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Text rendering."""

    @staticmethod
    def render_map(route=None, riders=None, res=None, cus=None):
        grid = [["." for _ in range(8)] for _ in range(8)]
        if route:
            for a, b in zip(route, route[1:]):
                steps = max(abs(a[0] - b[0]), abs(a[1] - b[1])) // 50 + 1
                for i in range(steps + 1):
                    t = i / steps
                    x = a[0] + (b[0] - a[0]) * t
                    y = a[1] + (b[1] - a[1]) * t
                    grid[to_cell(int(y))][to_cell(int(x))] = "*"
        if res:
            grid[to_cell(res[1])][to_cell(res[0])] = "M"
        if cus:
            grid[to_cell(cus[1])][to_cell(cus[0])] = "C"
        for r in riders or []:
            grid[to_cell(r.y)][to_cell(r.x)] = "R"
        lines = ["   " + " ".join(str(i) for i in range(8))]
        for i, row in enumerate(grid):
            lines.append("%d  %s" % (i, " ".join(row)))
        lines.append("R=rider M=restaurant C=customer *=route .=empty")
        return "\n".join(lines)

    @staticmethod
    def status():
        riders = globalvar.get_value("riders")
        out = ["Tick: %d  Funds: %d  Riders: %d" % (
            globalvar.get_value("tick"), globalvar.get_value("funds"),
            len(riders))]
        for r in riders:
            out.append("  Rider %d at (%d,%d) %s, orders: %s" % (
                r.rider_id, r.x, r.y, STATES[r.state],
                [o.id for o in r.orders]))
        out.append(DisplayManager.render_map(riders=riders))
        return "\n".join(out)

    @staticmethod
    def orders():
        orders = globalvar.get_value("orders")
        if not orders:
            return "No orders."
        out = []
        for o in orders:
            out.append(
                "Order %d: start=%d restaurant=%s customer=%s dist=%d "
                "time=%s rider=%s status=%s" % (
                    o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
                    o.time_taken if o.time_taken is not None else "-",
                    o.rider_id, o.status))
        return "\n".join(out)

    @staticmethod
    def riders():
        out = []
        for r in globalvar.get_value("riders"):
            out.append("Rider %d:" % r.rider_id)
            for e in r.log:
                out.append("  t=%d (%d,%d) %s order=%s" % (
                    e["time"], e["x"], e["y"], e["event"], e["order_id"]))
        return "\n".join(out) if out else "No riders."
