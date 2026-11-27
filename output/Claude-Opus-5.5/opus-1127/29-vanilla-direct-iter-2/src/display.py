"""Status display and ASCII map visualisation."""

from path_planner import PathPlanner, MAP_SIZE
from rider import STATE_NAMES
from system import SystemManager

RES = 50  # map resolution in units per character


class DisplayManager:
    """Builds textual views of the system state."""

    @staticmethod
    def _snap(v):
        return int(PathPlanner.clamp(int(round(v / RES)) * RES)) // RES

    @staticmethod
    def _route_cells(start, path):
        cells = set()
        cur = start
        for p in path:
            dx = p[0] - cur[0]
            dy = p[1] - cur[1]
            length = abs(dx) + abs(dy)
            steps = max(1, length // 25)
            for i in range(steps + 1):
                x = cur[0] + dx * i / steps
                y = cur[1] + dy * i / steps
                cells.add((DisplayManager._snap(x), DisplayManager._snap(y)))
            cur = p
        return cells

    @staticmethod
    def render_map(riders=None, orders=None, route_start=None, route=None):
        """Render the 8x8 grid map as ASCII text.

        Symbols: R rider, S restaurant, C customer, * route,
        # street, . empty block.
        """
        if riders is None:
            riders = SystemManager.riders()
        if orders is None:
            orders = [o for o in SystemManager.orders() if o.status != "completed"]
        n = MAP_SIZE // RES + 1
        grid = []
        for row in range(n):
            line = []
            for col in range(n):
                x, y = col * RES, row * RES
                line.append("#" if x % 100 == 0 or y % 100 == 0 else ".")
            grid.append(line)
        if route_start is not None and route:
            for cx, cy in DisplayManager._route_cells(route_start, route):
                grid[cy][cx] = "*"
        for o in orders:
            cx, cy = DisplayManager._snap(o.cus_pos[0]), DisplayManager._snap(o.cus_pos[1])
            grid[cy][cx] = "C"
        for o in orders:
            sx, sy = DisplayManager._snap(o.res_pos[0]), DisplayManager._snap(o.res_pos[1])
            grid[sy][sx] = "S"
        for r in riders:
            rx, ry = DisplayManager._snap(r.x), DisplayManager._snap(r.y)
            grid[ry][rx] = "R"
        header = "      " + " ".join(
            (str(c * RES // 100) if (c * RES) % 100 == 0 else " ") for c in range(n))
        lines = [header + "   (x in hundreds)"]
        for row in range(n):
            lines.append("%4d  %s" % (row * RES, " ".join(grid[row])))
        lines.append("Legend: R=Rider S=Restaurant C=Customer *=Route #=Street .=Block")
        return "\n".join(lines)

    @staticmethod
    def status_text():
        """Snapshot of funds and riders."""
        riders = SystemManager.riders()
        lines = [
            "=== System Status (time %d) ===" % SystemManager.current_time(),
            "Funds: %d" % SystemManager.funds(),
            "Riders: %d" % len(riders),
        ]
        for r in riders:
            lines.append("  Rider #%d at (%d, %d) | %s | speed %d | orders: %d %s%s" % (
                r.rider_id, r.x, r.y, STATE_NAMES.get(r.state, "?"), r.speed,
                len(r.orders), [o.id for o in r.orders],
                " | special case" if r.special_case else ""))
        pending = SystemManager.pending_orders()
        if pending:
            lines.append("Pending (unassigned) orders: %s" % [o.id for o in pending])
        return "\n".join(lines)

    @staticmethod
    def orders_text():
        """Details of every order."""
        orders = SystemManager.orders()
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-6s %-12s %-12s %-8s %-11s %-6s %-6s %-5s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Status", "Taken",
            "Eff", "Rider")]
        for o in orders:
            lines.append("%-4d %-6d %-12s %-12s %-8d %-11s %-6s %-6s %-5s" % (
                o.id, o.created_at, "(%d,%d)" % o.res_pos, "(%d,%d)" % o.cus_pos,
                o.distance, o.status,
                "-" if o.time_taken is None else o.time_taken,
                "-" if o.efficiency is None else o.efficiency,
                "-" if o.rider_id is None else "#%d" % o.rider_id))
        return "\n".join(lines)

    @staticmethod
    def riders_text():
        """Event history for every rider."""
        riders = SystemManager.riders()
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider #%d (delivered %d, travelled %d units):" % (
                r.rider_id, r.delivered_count, r.distance_travelled))
            for e in r.log:
                lines.append("  t=%-5s %-22s at (%d, %d)  order: %s" % (
                    e.get("time"), e.get("event"), e.get("x", 0), e.get("y", 0),
                    "-" if e.get("order_id") is None else e.get("order_id")))
        return "\n".join(lines)
