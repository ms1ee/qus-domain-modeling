"""Display manager."""
import globalvar
from path_planner import PathPlanner

STATES = {0: "idle", 1: "picking up", 2: "delivering"}


class DisplayManager:
    """Text output."""

    @staticmethod
    def map_text(route=None, riders=True):
        """ASCII 8x8 map. R rider, S restaurant, C customer, * route."""
        grid = [["." for _ in range(8)] for _ in range(8)]
        if route:
            for a, b in zip(route, route[1:]):
                for i in range(101):
                    px = a[0] + (b[0] - a[0]) * i // 100
                    py = a[1] + (b[1] - a[1]) * i // 100
                    grid[min(7, py // 100)][min(7, px // 100)] = "*"
        for o in globalvar.get_value("orders"):
            if o.status != "completed":
                grid[o.res_pos[1] // 100][o.res_pos[0] // 100] = "S"
                grid[o.cus_pos[1] // 100][o.cus_pos[0] // 100] = "C"
        if riders:
            for r in globalvar.get_value("riders"):
                grid[min(7, r.y // 100)][min(7, r.x // 100)] = "R"
        return "\n".join(" ".join(row) for row in reversed(grid))

    @staticmethod
    def status_text():
        """System snapshot."""
        rs = globalvar.get_value("riders")
        lines = ["Time: %d  Funds: %d  Riders: %d" % (
            globalvar.get_value("time"), globalvar.get_value("funds"),
            len(rs))]
        for r in rs:
            lines.append("Rider %d at (%d,%d) %s orders=%s" % (
                r.rider_id, r.x, r.y, STATES[r.state],
                [o.id for o in r.orders]))
        return "\n".join(lines)

    @staticmethod
    def orders_text():
        """All orders."""
        lines = []
        for o in globalvar.get_value("orders"):
            lines.append("Order %d start=%s res=%s cus=%s dist=%d time=%s "
                         "rider=%s status=%s" % (
                             o.id, o.create_time, o.res_pos, o.cus_pos,
                             o.distance, o.duration, o.rider_id, o.status))
        return "\n".join(lines) or "No orders."

    @staticmethod
    def riders_text():
        """Rider event logs."""
        lines = []
        for r in globalvar.get_value("riders"):
            for e in r.log:
                lines.append("t=%s rider %d %s order=%s pos=%s" % (
                    e["time"], r.rider_id, e["event"], e["order_id"],
                    e["pos"]))
        return "\n".join(lines) or "No riders."

    @staticmethod
    def route_text(order, rider):
        """Route description for a rider."""
        route = PathPlanner.route((rider.x, rider.y), order.res_pos,
                                  order.cus_pos)
        total = sum(abs(a[0] - b[0]) + abs(a[1] - b[1])
                    for a, b in zip(route, route[1:]))
        t = -(-total // rider.speed)
        return ("Route: %s\nSpeed: %d  Estimated time: %d ticks\n%s" % (
            " -> ".join(map(str, route)), rider.speed, t,
            DisplayManager.map_text(route)))
