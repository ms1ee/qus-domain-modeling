"""Status display and ASCII map visualisation."""

from config import MAP_CHARS, MAP_SIZE
from order_model import STATUS_COMPLETED

SCALE = MAP_SIZE // MAP_CHARS  # 50 units per character


def _cell(v):
    return max(0, min(MAP_CHARS - 1, int(v) // SCALE))


class DisplayManager:
    """Builds textual views of the system state."""

    @staticmethod
    def render_map(riders, orders, route=None):
        """Return a 16x16 ASCII map.

        Symbols: 'R' rider, 'S' restaurant, 'C' customer, '#' street,
        '.' empty, '*' route.
        """
        grid = []
        for row in range(MAP_CHARS):
            line = []
            for col in range(MAP_CHARS):
                line.append("#" if row % 2 == 0 or col % 2 == 0 else ".")
            grid.append(line)
        if route:
            for a, b in zip(route, route[1:]):
                dist = abs(a[0] - b[0]) + abs(a[1] - b[1])
                steps = max(1, dist // 10)
                for i in range(steps + 1):
                    x = a[0] + (b[0] - a[0]) * i / steps
                    y = a[1] + (b[1] - a[1]) * i / steps
                    grid[_cell(y)][_cell(x)] = "*"
        for o in orders:
            if o.status == STATUS_COMPLETED:
                continue
            grid[_cell(o.res_pos[1])][_cell(o.res_pos[0])] = "S"
            grid[_cell(o.cus_pos[1])][_cell(o.cus_pos[0])] = "C"
        for r in riders:
            grid[_cell(r.y)][_cell(r.x)] = "R"
        header = "    " + "".join("%-2d" % (c * 2 % 100 // 2 % 10)
                                  for c in range(0, MAP_CHARS, 2))
        lines = ["    " + "".join(str(c % 10) for c in range(MAP_CHARS))]
        del header
        for i, line in enumerate(grid):
            lines.append("%3d " % (i * SCALE) + "".join(line))
        lines.append("Legend: R=rider S=restaurant C=customer #=street "
                     ".=empty *=route (1 char = %d units)" % SCALE)
        return "\n".join(lines)

    @staticmethod
    def render_status(funds, riders, time):
        """System snapshot: funds and each rider's state/orders."""
        lines = ["Time: %d" % time, "Funds: %d" % funds,
                 "Riders: %d" % len(riders)]
        for r in riders:
            ids = [str(getattr(o, "id", "?")) for o in r.orders]
            active = [str(o.id) for o in r.active_orders()]
            lines.append(
                "  Rider %d @ (%d, %d) speed=%d state=%s orders=%d "
                "[all: %s] [active: %s]" % (
                    r.rider_id, r.x, r.y, r.speed, r.state_name,
                    len(r.orders), ", ".join(ids) or "-",
                    ", ".join(active) or "-"))
        return "\n".join(lines)

    @staticmethod
    def render_orders(orders):
        """Order detail table."""
        if not orders:
            return "No orders."
        lines = ["%-4s %-6s %-12s %-12s %-6s %-6s %-10s %-6s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Taken",
            "Status", "Rider")]
        for o in orders:
            lines.append("%-4s %-6s %-12s %-12s %-6s %-6s %-10s %-6s" % (
                o.id, o.created_time,
                "(%d,%d)" % o.res_pos, "(%d,%d)" % o.cus_pos,
                o.distance,
                "-" if o.time_taken is None else o.time_taken,
                o.status, "-" if o.rider_id is None else o.rider_id))
        return "\n".join(lines)

    @staticmethod
    def render_rider_logs(riders):
        """Every recorded status change for all riders."""
        if not riders:
            return "No riders."
        lines = []
        for r in riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s %-22s order=%-4s at (%s, %s)" % (
                    e.get("time"), e.get("event"),
                    "-" if e.get("order_id") is None else e.get("order_id"),
                    e.get("x"), e.get("y")))
        return "\n".join(lines)

    @staticmethod
    def render_route(rider, route, riders, orders):
        """Route map plus speed and estimated time for a rider."""
        from path_planner import PathPlanner
        length = PathPlanner.path_length(route)
        eta = -(-length // rider.speed) if rider.speed else 0
        lines = [
            "Route for rider %d: %s" % (
                rider.rider_id,
                " -> ".join("(%d,%d)" % (p[0], p[1]) for p in route)),
            "Speed: %d units/tick, route length: %d units, "
            "estimated time: %d ticks" % (rider.speed, length, eta),
            DisplayManager.render_map(riders, orders, route),
        ]
        return "\n".join(lines)
