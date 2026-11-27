"""Status display and ASCII map visualisation."""

from path_planner import PathPlanner, MAP_SIZE
from rider import STATE_NAMES

MAP_CHARS = 16
CELL = MAP_SIZE // MAP_CHARS  # 50 units per character


def _idx(value):
    return max(0, min(int(value) // CELL, MAP_CHARS - 1))


class DisplayManager:
    """Render system status, orders, rider logs and the ASCII map."""

    def __init__(self, system_manager):
        self.system = system_manager

    # ------------------------------------------------------------------
    @staticmethod
    def _base_grid():
        grid = []
        for row in range(MAP_CHARS):
            line = []
            for col in range(MAP_CHARS):
                line.append("#" if row % 2 == 0 or col % 2 == 0 else ".")
            grid.append(line)
        return grid

    @staticmethod
    def _draw_route(grid, points):
        for a, b in zip(points, points[1:]):
            dist = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
            steps = max(1, dist // (CELL // 2))
            for i in range(steps + 1):
                x = a[0] + (b[0] - a[0]) * i / steps
                y = a[1] + (b[1] - a[1]) * i / steps
                grid[_idx(y)][_idx(x)] = "*"

    def render_map(self, route=None, orders=None, riders=None):
        """Return a 16x16 ASCII map as a string."""
        grid = self._base_grid()
        if route:
            self._draw_route(grid, route)
        if orders is None:
            orders = [o for o in self.system.orders
                      if o.status != "completed"]
        for order in orders:
            grid[_idx(order.res_pos[1])][_idx(order.res_pos[0])] = "S"
            grid[_idx(order.cus_pos[1])][_idx(order.cus_pos[0])] = "C"
        if riders is None:
            riders = self.system.riders
        for rider in riders:
            grid[_idx(rider.y)][_idx(rider.x)] = "R"
        header = "    " + "".join("%d" % (i % 10) for i in range(MAP_CHARS))
        lines = [header]
        for i, row in enumerate(grid):
            lines.append("%3d " % (i * CELL) + "".join(row))
        lines.append("Legend: R=Rider S=Restaurant C=Customer "
                     "#=Street .=Empty *=Route (1 char = %d units)" % CELL)
        return "\n".join(lines)

    def render_route(self, rider, order):
        """Render the planned route for ``rider`` delivering ``order``."""
        points = PathPlanner.plan_full_route(
            (rider.x, rider.y), order.res_pos, order.cus_pos)
        length = PathPlanner.route_length(points)
        est = -(-length // rider.speed) if rider.speed > 0 else 0
        lines = [
            "Route for rider %s: %s" % (
                rider.rider_id, " -> ".join("(%d,%d)" % p for p in points)),
            "Speed: %d units/tick, distance: %d units, "
            "estimated time: %d ticks" % (rider.speed, length, est),
            self.render_map(route=points, orders=[order], riders=[rider]),
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    def render_status(self):
        """Return a snapshot of funds and rider states."""
        lines = ["=== System Status (tick %d) ===" % self.system.time,
                 "Funds: %d" % self.system.funds,
                 "Riders: %d" % len(self.system.riders)]
        for r in self.system.riders:
            ids = ", ".join(
                "#%d(%s)" % (o.id, o.status) for o in r.orders) or "none"
            lines.append("  Rider %d at (%d,%d) state=%s orders=%d [%s]" % (
                r.rider_id, r.x, r.y, STATE_NAMES.get(r.state, "?"),
                len(r.orders), ids))
        lines.append(self.render_map())
        return "\n".join(lines)

    def render_orders(self):
        """Return details for all orders."""
        orders = self.system.orders
        if not orders:
            return "No orders."
        lines = ["%-4s %-6s %-12s %-12s %-8s %-6s %-6s %-11s" % (
            "ID", "Start", "Restaurant", "Customer", "Distance", "Time",
            "Rider", "Status")]
        for o in orders:
            taken = o.time_taken()
            lines.append("%-4d %-6d %-12s %-12s %-8d %-6s %-6s %-11s" % (
                o.id, o.created_time,
                "(%d,%d)" % tuple(o.res_pos), "(%d,%d)" % tuple(o.cus_pos),
                o.distance, "-" if taken is None else str(taken),
                "-" if o.rider_id is None else str(o.rider_id), o.status))
        return "\n".join(lines)

    def render_rider_logs(self):
        """Return every logged status change of every rider."""
        if not self.system.riders:
            return "No riders."
        lines = []
        for r in self.system.riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s %-22s order=%-5s at (%s,%s)" % (
                    e.get("time"), e.get("event"),
                    "-" if e.get("order_id") is None else e.get("order_id"),
                    e.get("x"), e.get("y")))
        return "\n".join(lines)
