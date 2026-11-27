"""Display helpers."""
import globalvar
from pathplanner import PathPlanner

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Status and map rendering."""

    @staticmethod
    def map_text(riders=(), orders=(), route=None):
        grid = [["." for _ in range(8)] for _ in range(8)]
        if route:
            for a, b in zip(route, route[1:]):
                for i in range(0, 101, 10):
                    px = a[0] + (b[0] - a[0]) * i // 100
                    py = a[1] + (b[1] - a[1]) * i // 100
                    grid[min(7, py // 100)][min(7, px // 100)] = "#"
        for o in orders:
            grid[o.res_pos[1] // 100][o.res_pos[0] // 100] = "S"
            grid[o.cus_pos[1] // 100][o.cus_pos[0] // 100] = "C"
        for r in riders:
            grid[min(7, r.y // 100)][min(7, r.x // 100)] = "R"
        return "\n".join(" ".join(row) for row in grid)

    def status(self):
        riders = globalvar.get_value("riders")
        lines = ["Tick: %d  Funds: %d  Riders: %d" % (
            globalvar.get_value("tick"), globalvar.get_value("funds"),
            len(riders))]
        for r in riders:
            lines.append("Rider %d at (%d,%d) %s orders=%s" % (
                r.rider_id, r.x, r.y, STATES[r.state],
                [o.id for o in r.orders]))
        lines.append(self.map_text(
            riders, [o for r in riders for o in r.orders]))
        return "\n".join(lines)

    def orders(self):
        orders = globalvar.get_value("orders")
        if not orders:
            return "No orders."
        lines = []
        for o in orders:
            lines.append(
                "Order %d start=%d rest=%s cust=%s dist=%d time=%s rider=%s [%s]"
                % (o.id, o.start_time, o.res_pos, o.cus_pos, o.distance,
                   o.time_taken, o.rider_id, o.status))
        return "\n".join(lines)

    def riders(self):
        lines = []
        for r in globalvar.get_value("riders"):
            for e in r.log:
                lines.append("Rider %d t=%d (%d,%d) %s order=%s" % (
                    r.rider_id, e["time"], e["x"], e["y"], e["event"],
                    e["order_id"]))
        return "\n".join(lines) or "No riders."
