"""Status display and ASCII map visualisation."""

from grid_map import MAP_SIZE
from rider import RiderState

HALF = 50
CHAR_DIM = MAP_SIZE // HALF + 1  # 17


def _idx(v):
    return max(0, min(CHAR_DIM - 1, int((int(v) + HALF // 2) // HALF)))


class DisplayManager:
    """Builds textual views of the system state."""

    # ------------------------------------------------------------------- map
    def render_map(self, riders=None, orders=None, route=None):
        """Render the 8x8 grid map as ASCII.

        '#' streets, '.' empty cell, '*' route, 'S' restaurant,
        'C' customer, 'R' rider.
        """
        grid = [["#" if (i % 2 == 0 or j % 2 == 0) else "."
                 for i in range(CHAR_DIM)] for j in range(CHAR_DIM)]
        if route is not None:
            pts = route.as_tuples() if hasattr(route, "as_tuples") else route
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                c1, r1, c2, r2 = _idx(x1), _idx(y1), _idx(x2), _idx(y2)
                for c in range(min(c1, c2), max(c1, c2) + 1):
                    grid[r1][c] = "*"
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    grid[r][c2] = "*"
        for o in orders or []:
            if o.status == "completed":
                continue
            grid[_idx(o.res_pos[1])][_idx(o.res_pos[0])] = "S"
            grid[_idx(o.cus_pos[1])][_idx(o.cus_pos[0])] = "C"
        for r in riders or []:
            grid[_idx(r.y)][_idx(r.x)] = "R"
        lines = ["     " + " ".join(str(i // 2) if i % 2 else " "
                                    for i in range(CHAR_DIM))]
        for j, row in enumerate(grid):
            label = str(j // 2) if j % 2 else " "
            lines.append("  %s  %s" % (label, " ".join(row)))
        lines.append("Legend: R=rider S=restaurant C=customer "
                     "#=street .=empty *=route")
        return "\n".join(lines)

    # ---------------------------------------------------------------- status
    def show_status(self, sm):
        """Snapshot of funds and riders."""
        lines = ["=== System Status (tick %d) ===" % sm.current_tick,
                 "Funds: %d" % sm.funds,
                 "Riders: %d" % len(sm.riders)]
        for r in sm.riders:
            orders = ", ".join("#%d(%s)" % (o.id, o.status) for o in r.orders)
            lines.append("  Rider %d @(%d,%d) speed=%d state=%s%s orders=[%s]"
                         % (r.rider_id, r.x, r.y, r.speed,
                            RiderState.name(r.state),
                            " [special]" if r.special_case else "",
                            orders))
        return "\n".join(lines)

    def show_orders(self, orders):
        """Details of all orders."""
        if not orders:
            return "No orders yet."
        lines = ["=== Orders ===",
                 "%-4s %-6s %-11s %-11s %-6s %-8s %-6s %-11s" % (
                     "ID", "Start", "Restaurant", "Customer", "Dist",
                     "Travel", "Time", "Rider/Status")]
        for o in orders:
            lines.append("%-4d %-6d %-11s %-11s %-6d %-8s %-6s %s" % (
                o.id, o.start_time,
                "(%d,%d)" % o.res_pos, "(%d,%d)" % o.cus_pos,
                o.distance,
                o.travel_distance if o.status == "completed" else "-",
                o.time_taken if o.time_taken is not None else "-",
                "R%s/%s" % (o.rider_id if o.rider_id is not None else "-",
                            o.status)))
        return "\n".join(lines)

    def show_rider_logs(self, riders):
        """Every recorded status change of all riders."""
        if not riders:
            return "No riders yet."
        lines = ["=== Rider Logs ==="]
        for r in riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s (%d,%d) %-22s order=%s state=%s" % (
                    e.get("time"), e.get("x", 0), e.get("y", 0), e["event"],
                    "#%s" % e["order_id"] if e["order_id"] is not None else "-",
                    RiderState.name(e.get("state", 0))))
        return "\n".join(lines)

    def show_start_result(self, result, riders=None):
        """Summary of an order dispatch including the route map."""
        o = result["order"]
        r = result["rider"]
        route = result["route"]
        lines = [
            "Order #%d created." % o.id,
            "Restaurant grid: (%d,%d) center (%d,%d)" % (o.res_grid + o.res_pos),
            "Customer grid:   (%d,%d) center (%d,%d)" % (o.cus_grid + o.cus_pos),
            "New rider added: %s" % ("yes (%s)" % ", ".join(
                str(x.rider_id) for x in result.get("new_riders", []))
                if result["new_rider"] else "no"),
            "Assigned rider: %d  speed: %d units/tick" % (r.rider_id, r.speed),
            "Route: %s" % " -> ".join("(%d,%d)" % p for p in route.as_tuples()),
            "Route distance: %d  route time: %d ticks  wait: %d ticks  "
            "total: %d ticks" % (route.total_distance, route.estimated_time,
                                 result["wait_time"], result["total_time"]),
            self.render_map([r], [o], route),
        ]
        return "\n".join(lines)
