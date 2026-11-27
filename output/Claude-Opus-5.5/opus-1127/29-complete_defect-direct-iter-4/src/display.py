"""Status display and ASCII map visualisation."""

from rider import STATE_NAMES

GRID_CHARS = 17  # 8 cells + 9 street lines


def _idx(v):
    return max(0, min(GRID_CHARS - 1, int(round(v / 50.0))))


class DisplayManager:
    """Formats status information and renders the ASCII map."""

    @staticmethod
    def render_map(riders, orders, route=None):
        """Return an ASCII map.

        '#' street, '.' empty cell, '*' route, 'S' restaurant,
        'C' customer, 'R' rider.
        """
        grid = [['#' if (i % 2 == 0 or j % 2 == 0) else '.'
                 for j in range(GRID_CHARS)] for i in range(GRID_CHARS)]
        if route:
            for a, b in zip(route, route[1:]):
                r1, c1 = _idx(a[1]), _idx(a[0])
                r2, c2 = _idx(b[1]), _idx(b[0])
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    for c in range(min(c1, c2), max(c1, c2) + 1):
                        if r in (r1, r2) or c in (c1, c2):
                            grid[r][c] = '*'
            if len(route) == 1:
                grid[_idx(route[0][1])][_idx(route[0][0])] = '*'
        for o in orders:
            if o.status == "completed":
                continue
            grid[_idx(o.cus_pos[1])][_idx(o.cus_pos[0])] = 'C'
            grid[_idx(o.res_pos[1])][_idx(o.res_pos[0])] = 'S'
        for r in riders:
            grid[_idx(r.y)][_idx(r.x)] = 'R'
        header = "    " + " ".join(str(j // 2) if j % 2 else ' '
                                   for j in range(GRID_CHARS))
        lines = [header]
        for i, row in enumerate(grid):
            label = str(i // 2) if i % 2 else ' '
            lines.append(" %s  %s" % (label, " ".join(row)))
        lines.append("Legend: R=Rider S=Restaurant C=Customer "
                     "*=Route #=Street .=Empty")
        return "\n".join(lines)

    @staticmethod
    def status_text(sm):
        """Return a snapshot of the system state."""
        lines = ["=== System Status (time %d) ===" % sm.time,
                 "Funds: %d" % sm.funds,
                 "Riders: %d" % len(sm.riders)]
        for r in sm.riders:
            lines.append(
                "  Rider %d at (%d,%d) speed=%d state=%s%s orders=%s" % (
                    r.rider_id, r.x, r.y, r.speed,
                    STATE_NAMES.get(r.state, "?"),
                    " [special]" if r.special_case else "",
                    [o.id for o in r.orders]))
        pending = [o.id for o in sm.orders if o.status == "pending"]
        if pending:
            lines.append("Unassigned orders: %s" % pending)
        return "\n".join(lines)

    @staticmethod
    def orders_text(orders):
        """Return a table of all orders."""
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-6s %-11s %-11s %-6s %-6s %-6s %-11s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Time",
            "Rider", "Status")]
        for o in orders:
            lines.append("%-4s %-6s %-11s %-11s %-6s %-6s %-6s %-11s" % (
                o.id, o.create_time,
                "(%d,%d)" % tuple(o.res_pos), "(%d,%d)" % tuple(o.cus_pos),
                o.distance,
                o.time_taken if o.time_taken is not None else "-",
                o.rider_id if o.rider_id is not None else "-",
                o.status))
        return "\n".join(lines)

    @staticmethod
    def riders_log_text(riders):
        """Return all rider status-change records."""
        entries = []
        for r in riders:
            for e in r.log:
                entries.append((e.get("time", 0), r.rider_id, e))
        if not entries:
            return "No rider records."
        entries.sort(key=lambda t: (t[0], t[1]))
        lines = []
        for t, rid, e in entries:
            oid = e.get("order_id")
            lines.append("t=%-5s rider %-3s %-22s order=%-4s at (%s,%s)" % (
                t, rid, e.get("event"), oid if oid is not None else "-",
                e.get("x"), e.get("y")))
        return "\n".join(lines)

    @staticmethod
    def start_result_text(result, riders, orders):
        """Return the output of the start command."""
        o = result["order"]
        lines = [
            "Order %d created." % o.id,
            "Restaurant grid: (%d,%d) center (%d,%d)" % (
                o.res_grid + o.res_pos),
            "Customer grid:   (%d,%d) center (%d,%d)" % (
                o.cus_grid + o.cus_pos),
            "New rider added: %s" % (
                "yes (rider %d)" % result["new_rider"].rider_id
                if result["new_rider"] else "no"),
        ]
        rider = result["rider"]
        if rider is None:
            lines.append("No rider available; order queued.")
            return "\n".join(lines)
        lines.append("Assigned rider: %d  speed=%d units/tick  "
                     "estimated time=%s ticks" % (
                         rider.rider_id, rider.speed, result["eta"]))
        lines.append("Route: " + " -> ".join(
            "(%d,%d)" % p for p in result["route"]))
        lines.append(DisplayManager.render_map(riders, orders,
                                               result["route"]))
        return "\n".join(lines)
