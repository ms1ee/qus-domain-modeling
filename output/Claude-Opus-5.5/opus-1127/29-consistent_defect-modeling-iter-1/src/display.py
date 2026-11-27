"""Status display and ASCII map visualisation."""

from grid_map import MAP_SIZE
from rider import STATE_NAMES

MAP_CELLS = 16
UNIT = MAP_SIZE // MAP_CELLS  # 50 units per character


def _cell(v):
    return max(0, min(MAP_CELLS - 1, int(v) // UNIT))


class DisplayManager:
    """Builds text output for the command line interface."""

    def __init__(self, map_size=MAP_CELLS):
        self.map_size = map_size

    def render_map(self, riders, orders=(), route=None):
        """Render a 16x16 ASCII map.

        '#' street, '.' empty, '*' route, 'S' restaurant, 'C' customer,
        'R' rider.
        """
        n = self.map_size
        grid = [["#" if (r % 2 == 0 or c % 2 == 0) else "." for c in range(n)]
                for r in range(n)]
        if route:
            for (ax, ay), (bx, by) in zip(route, route[1:]):
                steps = max(abs(bx - ax), abs(by - ay)) // (UNIT // 2) or 1
                for i in range(steps + 1):
                    x = ax + (bx - ax) * i / steps
                    y = ay + (by - ay) * i / steps
                    grid[_cell(y)][_cell(x)] = "*"
        for o in orders:
            if o.status == "completed":
                continue
            grid[_cell(o.res_y)][_cell(o.res_x)] = "S"
            grid[_cell(o.cus_y)][_cell(o.cus_x)] = "C"
        for r in riders:
            grid[_cell(r.y)][_cell(r.x)] = "R"
        header = "    " + "".join("%-2d" % (c % 100) if c % 2 == 0 else ""
                                    for c in range(n))
        lines = ["   x→ (each char = %d units)" % UNIT]
        lines.append("    " + "".join(str((c * UNIT) // 100) if c % 2 == 0 else " "
                                      for c in range(n)))
        del header
        for r in range(n):
            label = str((r * UNIT) // 100) if r % 2 == 0 else " "
            lines.append("%3s " % label + "".join(grid[r]))
        lines.append("Legend: R=rider S=restaurant C=customer *=route #=street .=empty")
        return "\n".join(lines)

    @staticmethod
    def format_status(manager):
        """System status snapshot text."""
        lines = ["=== System Status (tick %d) ===" % manager.current_tick,
                 "Funds: %d" % manager.funds,
                 "Riders: %d" % len(manager.riders)]
        for r in manager.riders:
            active = [o.id for o in r.orders if o.status != "completed"]
            done = [o.id for o in r.orders if o.status == "completed"]
            lines.append("  Rider %d @ (%d,%d) speed=%d state=%s orders=%d "
                         "active=%s done=%s" % (r.rider_id, r.x, r.y, r.speed,
                                                r.state_name, len(r.orders),
                                                active, done))
        return "\n".join(lines)

    @staticmethod
    def format_orders(orders):
        """Order details table."""
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-6s %-11s %-11s %-6s %-11s %-6s %-5s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Status",
            "Taken", "Rider")]
        for o in orders:
            lines.append("%-4d %-6d %-11s %-11s %-6d %-11s %-6s %-5s" % (
                o.id, o.start_time, "(%d,%d)" % o.res_pos, "(%d,%d)" % o.cus_pos,
                o.distance, o.status,
                "-" if o.time_taken is None else o.time_taken,
                "-" if o.rider_id is None else o.rider_id))
        return "\n".join(lines)

    @staticmethod
    def format_rider_logs(riders):
        """All rider status changes."""
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                frm = e.get("from_state")
                to = e.get("to_state")
                lines.append("  t=%-5s %-22s order=%-4s at (%d,%d) %s -> %s" % (
                    e.get("time"), e["event"],
                    "-" if e["order_id"] is None else e["order_id"],
                    e.get("x", 0), e.get("y", 0),
                    "-" if frm is None else STATE_NAMES.get(frm, frm),
                    STATE_NAMES.get(to, to)))
        return "\n".join(lines)
