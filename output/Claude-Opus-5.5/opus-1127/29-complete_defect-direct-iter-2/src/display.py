"""Status display and ASCII map visualisation."""

from path_planner import PathPlanner
from rider import STATE_NAMES

N = 17  # characters per side: 9 street lines + 8 cells


def _cell(x, y):
    col = min(N - 1, max(0, int(x) // 50))
    row = min(N - 1, max(0, int(y) // 50))
    return row, col


class DisplayManager:
    """Builds textual representations of the system state."""

    def _base(self):
        return [['#' if (r % 2 == 0 or c % 2 == 0) else '.'
                 for c in range(N)] for r in range(N)]

    @staticmethod
    def _mark(grid, r, c, ch):
        cur = grid[r][c]
        if (cur == '-' and ch == '|') or (cur == '|' and ch == '-') \
                or cur == '+':
            grid[r][c] = '+'
        else:
            grid[r][c] = ch

    def _draw_route(self, grid, route):
        for a, b in zip(route, route[1:]):
            r1, c1 = _cell(*a)
            r2, c2 = _cell(*b)
            if r1 == r2:
                for c in range(min(c1, c2), max(c1, c2) + 1):
                    self._mark(grid, r1, c, '-')
            else:
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    self._mark(grid, r, c1, '|')
        for p in route[1:-1]:
            r, c = _cell(*p)
            grid[r][c] = '+'

    def render_map(self, riders, orders=None, route=None, title=None):
        """Render the 8x8 grid as ASCII art."""
        grid = self._base()
        if route:
            self._draw_route(grid, route)
        for o in orders or []:
            if o.status == "completed":
                continue
            r, c = _cell(*o.res_pos)
            grid[r][c] = 'S'
            r, c = _cell(*o.cus_pos)
            grid[r][c] = 'C'
        for rd in riders or []:
            r, c = _cell(rd.x, rd.y)
            grid[r][c] = 'R'
        lines = []
        if title:
            lines.append(title)
        header = [str(c // 2) if c % 2 else ' ' for c in range(N)]
        lines.append("    " + " ".join(header))
        for r in range(N):
            label = str(r // 2) if r % 2 else ' '
            lines.append("%3s " % label + " ".join(grid[r]))
        lines.append("Legend: R=Rider S=Restaurant C=Customer "
                     "#=Street .=Block -|+=Route")
        return "\n".join(lines)

    def show_route(self, rider, order, route, distance, eta):
        """Render the route map for an assigned rider."""
        title = ("Route for rider %d (speed %d units/tick): distance %d, "
                 "estimated time %d ticks"
                 % (rider.rider_id, rider.speed, distance, eta))
        pts = " -> ".join("(%d,%d)" % p for p in route)
        return "\n".join([self.render_map([rider], [order], route, title),
                          "Waypoints: " + pts])

    def show_status(self, funds, tick, riders, orders):
        """Snapshot of the system state."""
        pending = [o.id for o in orders if o.status == "pending"]
        lines = ["=== System Status (tick %d) ===" % tick,
                 "Funds: %d" % funds,
                 "Riders: %d" % len(riders),
                 "Orders: %d total, %d completed, pending: %s" % (
                     len(orders),
                     len([o for o in orders if o.status == "completed"]),
                     pending or "none")]
        for r in riders:
            lines.append(
                "  Rider %d: pos=(%d,%d) grid=%s speed=%d state=%s "
                "orders=%s special=%s delivered=%d" % (
                    r.rider_id, r.x, r.y, PathPlanner.cell_of(r.x, r.y),
                    r.speed, STATE_NAMES.get(r.state, "?"),
                    [o.id for o in r.orders], r.special_case,
                    r.completed_count))
        return "\n".join(lines)

    def show_orders(self, orders):
        """Table with details of all orders."""
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-6s %-20s %-20s %-6s %-8s %-6s %-11s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Taken",
            "Rider", "Status")]
        for o in orders:
            taken = o.time_taken
            lines.append("%-4d %-6d %-20s %-20s %-6d %-8s %-6s %-11s" % (
                o.id, o.create_time,
                "%s->%s" % (tuple(o.raw_res), tuple(o.res_pos)),
                "%s->%s" % (tuple(o.raw_cus), tuple(o.cus_pos)),
                o.distance, "-" if taken is None else str(taken),
                "-" if o.rider_id is None else str(o.rider_id), o.status))
        return "\n".join(lines)

    def show_rider_logs(self, riders):
        """All recorded rider status changes."""
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s %-22s pos=(%s,%s) order=%s" % (
                    e.get("time"), e.get("event"), e.get("x"), e.get("y"),
                    e.get("order_id") if e.get("order_id") is not None
                    else "-"))
        return "\n".join(lines)
