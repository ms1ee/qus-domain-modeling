"""Status display and ASCII map rendering."""

import globalvar
from order import OrderManager
from path_planner import PathPlanner
from rider import RiderState

SIZE = 17  # 8 cells + 9 street lines


def _to_char(v):
    return max(0, min(SIZE - 1, int(round(v / 50.0))))


class DisplayManager:
    """Formats system status, order tables, rider logs and maps."""

    def _base_grid(self):
        grid = []
        for r in range(SIZE):
            row = []
            for c in range(SIZE):
                row.append("#" if (r % 2 == 0 or c % 2 == 0) else ".")
            grid.append(row)
        return grid

    @staticmethod
    def _draw_route(grid, points):
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            length = abs(x2 - x1) + abs(y2 - y1)
            steps = max(1, length // 10)
            for i in range(steps + 1):
                x = x1 + (x2 - x1) * i / float(steps)
                y = y1 + (y2 - y1) * i / float(steps)
                grid[_to_char(y)][_to_char(x)] = "*"

    def render_map(self, riders=None, orders=None, route=None):
        """Return the ASCII map as a string."""
        grid = self._base_grid()
        if route:
            self._draw_route(grid, route)
        if orders is None:
            orders = [o for o in OrderManager.all_orders() if o.status != "completed"]
        for o in orders:
            if o.status in ("pending", "assigned", "picking_up"):
                grid[_to_char(o.res_y)][_to_char(o.res_x)] = "S"
            grid[_to_char(o.cus_y)][_to_char(o.cus_x)] = "C"
        if riders is None:
            riders = globalvar.get_value("riders", []) or []
        for r in riders:
            grid[_to_char(r.y)][_to_char(r.x)] = "R"
        header = "      " + " ".join(str(c // 2) if c % 2 == 0 else " "
                                     for c in range(SIZE))
        lines = [header]
        for r in range(SIZE):
            label = "%4d  " % (r * 50) if r % 2 == 0 else "      "
            lines.append(label + " ".join(grid[r]))
        lines.append("Legend: R=Rider S=Restaurant C=Customer *=Route "
                     "#=Street .=Empty (x header in hundreds)")
        return "\n".join(lines)

    def render_route(self, rider):
        """Return the route map and summary for a rider."""
        points = rider.planned_waypoints()
        length = PathPlanner.path_length(points)
        eta = PathPlanner.estimate_time(length, rider.speed)
        orders = [o for o in rider.orders if o.status != "completed"]
        text = [self.render_map(riders=[rider], orders=orders, route=points)]
        text.append("Route waypoints: " + " -> ".join("(%d,%d)" % p for p in points))
        text.append("Rider #%s speed: %s units/tick, route length: %s, "
                    "estimated time: %s ticks" % (rider.rider_id, rider.speed, length, eta))
        return "\n".join(text)

    def render_status(self):
        """Return a snapshot of the system state."""
        riders = globalvar.get_value("riders", []) or []
        lines = ["=== System Status (tick %s) ===" % globalvar.get_value("current_tick", 0),
                 "Funds: %s" % globalvar.get_value("funds", 0),
                 "Riders: %d" % len(riders)]
        for r in riders:
            lines.append("  Rider #%s at (%s,%s) state=%s orders=%d %s%s" % (
                r.rider_id, r.x, r.y, RiderState.name(r.state), len(r.orders),
                [o.id for o in r.orders], " [special]" if r.special_case else ""))
        stats = OrderManager.statistics()
        lines.append("Orders: %d total, %d completed, avg time: %s" % (
            stats["total"], stats["completed"], stats["avg_time"]))
        return "\n".join(lines)

    def render_orders(self):
        """Return a table of all orders."""
        orders = OrderManager.all_orders()
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-6s %-12s %-12s %-8s %-8s %-6s %-11s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Taken", "Rider", "Status")]
        for o in orders:
            lines.append("%-4s %-6s %-12s %-12s %-8s %-8s %-6s %-11s" % (
                o.id, o.start_time, "(%d,%d)" % o.res_pos, "(%d,%d)" % o.cus_pos,
                o.distance, "-" if o.time_taken is None else o.time_taken,
                "-" if o.rider_id is None else o.rider_id, o.status))
        return "\n".join(lines)

    def render_rider_logs(self):
        """Return every rider's status change log."""
        riders = globalvar.get_value("riders", []) or []
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider #%s:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s %-22s order=%-4s at (%s,%s) state=%s" % (
                    e.get("time"), e.get("event"),
                    "-" if e.get("order_id") is None else e.get("order_id"),
                    e.get("x"), e.get("y"), RiderState.name(e.get("state"))))
        return "\n".join(lines)
