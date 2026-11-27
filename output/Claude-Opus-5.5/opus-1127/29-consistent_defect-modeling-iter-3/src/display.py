"""Status displays and ASCII map visualization."""

from rider import RiderState


class DisplayManager:
    """Formats system information for the command line."""

    def __init__(self, map_size=16, map_units=800):
        self.map_size = map_size
        self.scale = map_units // map_size  # 50 units per character

    def _idx(self, v):
        return max(0, min(self.map_size, int(round(v / float(self.scale)))))

    def render_map(self, riders, orders, routes=None):
        """Render a 16x16-cell ASCII map ('#' streets, '.' blocks)."""
        n = self.map_size + 1
        grid = []
        for row in range(n):
            y = row * self.scale
            line = []
            for col in range(n):
                x = col * self.scale
                line.append("#" if (x % 100 == 0 or y % 100 == 0) else ".")
            grid.append(line)
        for route in routes or []:
            pts = route.points
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                c1, r1, c2, r2 = self._idx(x1), self._idx(y1), self._idx(x2), self._idx(y2)
                steps = max(abs(c2 - c1), abs(r2 - r1), 1)
                for s in range(steps + 1):
                    c = c1 + (c2 - c1) * s // steps
                    r = r1 + (r2 - r1) * s // steps
                    grid[r][c] = "*"
        for o in orders:
            if o.status == "completed":
                continue
            grid[self._idx(o.res_pos[1])][self._idx(o.res_pos[0])] = "S"
            grid[self._idx(o.cus_pos[1])][self._idx(o.cus_pos[0])] = "C"
        for r in riders:
            grid[self._idx(r.y)][self._idx(r.x)] = "R"
        header = "     " + "".join(str((c * self.scale // 100) % 10) if c % 2 == 0
                                   else " " for c in range(n))
        lines = [header]
        for i, row in enumerate(grid):
            lines.append("%4d " % (i * self.scale) + "".join(row))
        lines.append("Legend: R=Rider S=Restaurant C=Customer #=street .=block *=route")
        return "\n".join(lines)

    @staticmethod
    def format_status(system):
        lines = ["Tick: %d" % system.current_tick,
                 "Funds: %d" % system.funds,
                 "Riders: %d" % len(system.riders)]
        for r in system.riders:
            lines.append("  Rider %d at (%d, %d) speed=%d state=%s orders=%d active=%d%s" % (
                r.rider_id, r.x, r.y, r.speed, RiderState.NAMES.get(r.state, r.state),
                len(r.orders), len(r.active_orders),
                " [special]" if r.special_case else ""))
            for o in r.orders:
                lines.append("     order #%d %s -> %s [%s]" % (
                    o.id, tuple(o.res_pos), tuple(o.cus_pos), o.status))
        return "\n".join(lines)

    @staticmethod
    def format_orders(orders):
        if not orders:
            return "No orders."
        lines = ["%-5s %-6s %-12s %-12s %-9s %-6s %-6s %-11s" % (
            "ID", "Start", "Restaurant", "Customer", "Distance", "Time", "Rider",
            "Status")]
        for o in orders:
            lines.append("%-5d %-6d %-12s %-12s %-9s %-6s %-6s %-11s" % (
                o.id, o.start_time or 0, "(%d,%d)" % tuple(o.res_pos),
                "(%d,%d)" % tuple(o.cus_pos), o.distance,
                "-" if o.time_taken is None else o.time_taken,
                "-" if o.rider_id is None else o.rider_id, o.status))
        return "\n".join(lines)

    @staticmethod
    def format_rider_logs(riders):
        if not riders:
            return "No riders."
        lines = []
        for r in riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s (%s, %s) %-22s order=%s" % (
                    e.get("time"), e.get("x"), e.get("y"), e.get("event"),
                    "-" if e.get("order_id") is None else e.get("order_id")))
        return "\n".join(lines)

    @staticmethod
    def format_route_info(rider, route):
        return "Rider %d route: %s\n  length=%d speed=%d estimated time=%d ticks" % (
            rider.rider_id, " -> ".join("(%d,%d)" % p for p in route.points),
            route.length, rider.speed, route.estimated_time)
