"""Status display and ASCII map rendering."""

from grid_map import MAP_SIZE, to_grid_point

STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}
EVENT_NAMES = {
    "spawn": "joined the fleet",
    "accepted_order": "accepted order",
    "arrived_at_merchant": "arrived at restaurant",
    "delivered_to_customer": "delivered to customer",
}

UNIT = 50
SIZE = MAP_SIZE // UNIT + 1  # 17 characters per side


def _idx(v):
    return max(0, min(SIZE - 1, int(round(v / UNIT))))


class DisplayManager:
    """Formats system information for the command line."""

    def render_map(self, riders=(), orders=(), route=None):
        """Return an ASCII map.

        Even rows/columns are streets ('#'), odd/odd positions are blocks
        ('.'). Routes are drawn with '-', '|' and '+'; 'S' restaurant,
        'C' customer, 'R' rider.
        """
        grid = [["#" if (r % 2 == 0 or c % 2 == 0) else "." for c in range(SIZE)]
                for r in range(SIZE)]
        if route is not None and len(route.points) > 1:
            pts = route.points
            for a, b in zip(pts, pts[1:]):
                ra, ca, rb, cb = _idx(a[1]), _idx(a[0]), _idx(b[1]), _idx(b[0])
                if ra == rb:
                    for c in range(min(ca, cb), max(ca, cb) + 1):
                        grid[ra][c] = "-"
                else:
                    for r in range(min(ra, rb), max(ra, rb) + 1):
                        grid[r][ca] = "|"
            for p in pts[1:-1]:
                grid[_idx(p[1])][_idx(p[0])] = "+"
        for o in orders:
            grid[_idx(o.cus_pos[1])][_idx(o.cus_pos[0])] = "C"
        for o in orders:
            grid[_idx(o.res_pos[1])][_idx(o.res_pos[0])] = "S"
        for rd in riders:
            grid[_idx(rd.y)][_idx(rd.x)] = "R"
        header = "    " + " ".join(str(i // 2) if i % 2 else " " for i in range(SIZE))
        lines = [header]
        for r in range(SIZE):
            label = str(r // 2) if r % 2 else " "
            lines.append(" %s  %s" % (label, " ".join(grid[r])))
        lines.append("Legend: R=Rider S=Restaurant C=Customer #=Street .=Block "
                     "-|+=Route (grid lines every 100 units)")
        return "\n".join(lines)

    def format_order_result(self, result):
        """Format the output of a ``start`` command."""
        o, rider, route = result["order"], result["rider"], result["route"]
        lines = [
            "Order #%d created at t=%d" % (o.id, o.start_time),
            "Restaurant: input %s -> grid cell %s, center %s" % (o.raw_res, o.res_grid, o.res_pos),
            "Customer:   input %s -> grid cell %s, center %s" % (o.raw_cus, o.cus_grid, o.cus_pos),
        ]
        rec = result["recruited"]
        lines.append("New rider added: %s" % ("Yes (Rider #%d)" % rec.rider_id if rec else "No"))
        lines.append("Assigned to Rider #%d (speed %d units/tick)%s" % (
            rider.rider_id, rider.speed,
            " - queued after current deliveries" if result["busy"] else ""))
        lines.append("Route: " + " -> ".join("(%d,%d)" % p for p in route.points))
        lines.append("Route distance: %d units, estimated time: %d ticks%s" % (
            route.total_distance, result["eta"],
            " [special case: directly above/below]" if route.special_case else ""))
        start_marker = _FakeRider(route.points[0]) if route.points else None
        lines.append(self.render_map([start_marker] if start_marker else [], [o], route))
        return "\n".join(lines)

    def format_status(self, funds, time, riders):
        """Snapshot of funds and rider states."""
        lines = ["=== System Status (t=%d) ===" % time,
                 "Funds: %d" % funds,
                 "Riders: %d" % len(riders)]
        for r in riders:
            ids = [o.id for o in r.pending_orders()]
            lines.append("  Rider #%d at (%d,%d) grid %s | %s | speed %d | orders %s%s" % (
                r.rider_id, r.x, r.y, to_grid_point((r.x, r.y)),
                STATE_NAMES.get(int(r.state), "?"), r.speed, ids or "[]",
                " | special case" if r.special_case else ""))
        return "\n".join(lines)

    def format_orders(self, orders):
        """Table of all orders."""
        if not orders:
            return "No orders yet."
        head = "%-4s %-6s %-12s %-12s %-8s %-6s %-6s %-11s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Taken", "Rider", "Status")
        lines = [head, "-" * len(head)]
        for o in orders:
            lines.append("%-4d %-6d %-12s %-12s %-8d %-6s %-6s %-11s" % (
                o.id, o.start_time, "(%d,%d)" % o.res_pos, "(%d,%d)" % o.cus_pos,
                o.distance, "-" if o.time_taken is None else o.time_taken,
                "-" if o.rider_id is None else o.rider_id, o.status))
        return "\n".join(lines)

    def format_rider_logs(self, riders):
        """All status-change records of all riders."""
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider #%d:" % r.rider_id)
            for e in r.log:
                oid = "" if e.get("order_id") is None else " #%s" % e["order_id"]
                lines.append("  t=%-5s (%d,%d) %s%s" % (
                    e.get("time"), e.get("x", 0), e.get("y", 0),
                    EVENT_NAMES.get(e["event"], e["event"]), oid))
        return "\n".join(lines)

    def format_map(self, riders, orders):
        """Map of all riders and active orders."""
        active = [o for o in orders if o.status != "completed"]
        return self.render_map(riders, active)


class _FakeRider:
    """Lightweight marker used to draw a route's start point as 'R'."""

    def __init__(self, pos):
        self.x, self.y = pos
