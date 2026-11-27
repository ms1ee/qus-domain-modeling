"""Status display and ASCII map visualisation."""

from path_planner import MAP_SIZE
from rider import STATE_NAMES

HALF = 50
SIZE = MAP_SIZE // HALF + 1  # 17 columns / rows


def _idx(v):
    return max(0, min(SIZE - 1, int(v) // HALF))


class DisplayManager:
    """Builds text output for the command line."""

    def render_map(self, riders, orders, path_start=None, path=None,
                   highlight=None):
        """Render the 8x8 grid map.

        '#' streets, '.' cell interior, '*' route, 'S' restaurant,
        'C' customer, 'R' rider (highlighted rider shown as '@' if given).
        """
        grid = [["#" if (r % 2 == 0 or c % 2 == 0) else "."
                 for c in range(SIZE)] for r in range(SIZE)]
        if path_start is not None and path:
            cx, cy = path_start
            for px, py in path:
                x0, x1 = sorted((_idx(cx), _idx(px)))
                y0, y1 = sorted((_idx(cy), _idx(py)))
                for row in range(y0, y1 + 1):
                    for col in range(x0, x1 + 1):
                        grid[row][col] = "*"
                cx, cy = px, py
        for o in orders:
            if o.status == "completed":
                continue
            grid[_idx(o.res_pos[1])][_idx(o.res_pos[0])] = "S"
            grid[_idx(o.cus_pos[1])][_idx(o.cus_pos[0])] = "C"
        for r in riders:
            grid[_idx(r.y)][_idx(r.x)] = "R"
        if highlight is not None:
            grid[_idx(highlight.y)][_idx(highlight.x)] = "R"
        header = "      " + " ".join(
            (str(i // 2) if i % 2 == 1 else " ") for i in range(SIZE))
        lines = [header]
        for i, row in enumerate(grid):
            label = "%3d" % (i * HALF) if i % 2 == 0 else "  %d" % (i // 2)
            lines.append("%s   %s" % (label, " ".join(row)))
        lines.append("Legend: R=rider S=restaurant C=customer "
                     "#=street .=empty *=route")
        return "\n".join(lines)

    def render_status(self, funds, time, riders):
        """System snapshot."""
        lines = ["=== System Status (t=%d) ===" % time,
                 "Funds: %d" % funds,
                 "Riders: %d" % len(riders)]
        for r in riders:
            lines.append(
                "  Rider %d | pos=(%d,%d) speed=%d | %s | orders=%s%s" % (
                    r.rider_id, r.x, r.y, r.speed,
                    STATE_NAMES.get(r.state, "?"),
                    [o.id for o in r.orders],
                    " | special" if r.special_case else ""))
        return "\n".join(lines)

    def render_orders(self, orders):
        """Table of all orders."""
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-6s %-11s %-11s %-6s %-6s %-6s %-11s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Time",
            "Rider", "Status")]
        for o in orders:
            dist = o.distance if o.distance is not None else o.trip_distance
            lines.append("%-4d %-6d %-11s %-11s %-6s %-6s %-6s %-11s" % (
                o.id, o.create_time, "(%d,%d)" % o.res_pos,
                "(%d,%d)" % o.cus_pos, dist,
                o.time_taken if o.time_taken is not None else "-",
                o.rider_id if o.rider_id is not None else "-", o.status))
        return "\n".join(lines)

    def render_rider_logs(self, riders):
        """Every status change of all riders."""
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-4s %-22s order=%-4s pos=(%d,%d)" % (
                    e.get("time"), e["event"],
                    e["order_id"] if e["order_id"] is not None else "-",
                    e.get("x", 0), e.get("y", 0)))
        return "\n".join(lines)
