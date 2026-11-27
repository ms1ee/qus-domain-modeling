"""Status displays and ASCII map visualisation."""

import globalvar
from rider import RiderState
from path_planner import MAP_SIZE

MAP_CHARS = 16


class DisplayManager:
    """Formats system state into text."""

    def __init__(self, map_size=MAP_CHARS):
        self.map_size = map_size
        self.unit = MAP_SIZE // map_size

    def _idx(self, v):
        return max(0, min(self.map_size - 1, int(v) // self.unit))

    def render_map(self, route_points=None, highlight_orders=None):
        """Return the ASCII map as a string."""
        n = self.map_size
        grid = []
        for r in range(n):
            row = []
            for c in range(n):
                row.append("#" if r % 2 == 0 or c % 2 == 0 else ".")
            grid.append(row)
        if route_points and len(route_points) > 1:
            for (x1, y1), (x2, y2) in zip(route_points, route_points[1:]):
                steps = max(abs(x2 - x1), abs(y2 - y1)) // self.unit + 1
                for i in range(steps + 1):
                    t = i / steps if steps else 0
                    x = x1 + (x2 - x1) * t
                    y = y1 + (y2 - y1) * t
                    grid[self._idx(y)][self._idx(x)] = "*"
        orders = highlight_orders
        if orders is None:
            orders = [o for o in globalvar.get_value("orders") or []
                      if not o.completed]
        for o in orders:
            grid[self._idx(o.res_pos[1])][self._idx(o.res_pos[0])] = "S"
            grid[self._idx(o.cus_pos[1])][self._idx(o.cus_pos[0])] = "C"
        for rider in globalvar.get_value("riders") or []:
            grid[self._idx(rider.y)][self._idx(rider.x)] = "R"
        header = "    " + "".join("%-2d" % (c % 100) if c % 2 == 0 else ""
                                  for c in range(n))
        lines = [header.rstrip()]
        for r in range(n):
            lines.append("%4d " % (r * self.unit) + " ".join(grid[r]))
        lines.append("Legend: R=rider S=restaurant C=customer *=route "
                     "#=street .=empty (1 char = %d units)" % self.unit)
        return "\n".join(lines)

    def status_text(self):
        """Snapshot of funds and riders."""
        riders = globalvar.get_value("riders") or []
        lines = ["Tick: %s" % globalvar.get_value("current_tick", 0),
                 "Funds: %s" % globalvar.get_value("funds"),
                 "Riders: %d" % len(riders)]
        for r in riders:
            ids = [o.id for o in r.orders]
            lines.append("  Rider %d at (%d, %d) speed=%d state=%s "
                         "active=%d orders=%s" % (
                             r.rider_id, r.x, r.y, r.speed,
                             RiderState.name(r.state),
                             len(r.active_orders()), ids))
        return "\n".join(lines)

    def orders_text(self):
        """Details of every order."""
        orders = globalvar.get_value("orders") or []
        if not orders:
            return "No orders."
        lines = ["%-4s %-6s %-12s %-12s %-8s %-6s %-6s %-10s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Time",
            "Rider", "Status")]
        for o in orders:
            lines.append("%-4d %-6d %-12s %-12s %-8s %-6s %-6s %-10s" % (
                o.id, o.start_time, "(%d,%d)" % o.res_pos,
                "(%d,%d)" % o.cus_pos, o.distance,
                "-" if o.time_taken is None else o.time_taken,
                "-" if o.rider_id is None else o.rider_id, o.status))
        return "\n".join(lines)

    def riders_text(self):
        """Status change history of all riders."""
        riders = globalvar.get_value("riders") or []
        if not riders:
            return "No riders."
        lines = []
        for r in riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s (%s, %s) %-22s order=%s" % (
                    e.get("time"), e.get("x"), e.get("y"), e["event"],
                    "-" if e["order_id"] is None else e["order_id"]))
        return "\n".join(lines)
