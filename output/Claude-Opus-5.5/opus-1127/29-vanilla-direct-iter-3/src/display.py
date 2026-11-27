"""Status display and ASCII map visualisation."""

import globalvar as gv
from rider import STATE_NAMES

CHAR_DIM = 17  # 8 cells + 9 street lines


def _idx(v):
    """Map a coordinate (0..800) to a character index (0..16)."""
    return max(0, min(CHAR_DIM - 1, int(round(v / 50.0))))


class DisplayManager:
    """Formats status information and ASCII maps."""

    @staticmethod
    def render_map(riders, orders, route=None):
        """Return an ASCII map string.

        '#' streets, '.' empty cell, 'S' restaurant, 'C' customer,
        'R' rider, '*' planned route.
        """
        grid = [["#" if (r % 2 == 0 or c % 2 == 0) else "."
                 for c in range(CHAR_DIM)] for r in range(CHAR_DIM)]
        if route and len(route) > 1:
            for a, b in zip(route, route[1:]):
                c0, r0 = _idx(a[0]), _idx(a[1])
                c1, r1 = _idx(b[0]), _idx(b[1])
                if c0 == c1:
                    step = 1 if r1 >= r0 else -1
                    for r in range(r0, r1 + step, step):
                        grid[r][c0] = "*"
                else:
                    step = 1 if c1 >= c0 else -1
                    for c in range(c0, c1 + step, step):
                        grid[r0][c] = "*"
        for order in orders:
            if order.status == "completed":
                continue
            grid[_idx(order.cus_pos[1])][_idx(order.cus_pos[0])] = "C"
        for order in orders:
            if order.status in ("completed", "delivering"):
                continue
            grid[_idx(order.res_pos[1])][_idx(order.res_pos[0])] = "S"
        for rider in riders:
            grid[_idx(rider.y)][_idx(rider.x)] = "R"
        header = "    " + "".join(str((c // 2) % 10) if c % 2 else " "
                                  for c in range(CHAR_DIM))
        lines = [header]
        for r in range(CHAR_DIM):
            label = str(r // 2) if r % 2 else " "
            lines.append("  %s %s" % (label, "".join(grid[r])))
        lines.append("Legend: R=rider S=restaurant C=customer "
                     "#=street .=empty *=route")
        return "\n".join(lines)

    @staticmethod
    def format_status(riders):
        """Snapshot of funds and rider states."""
        lines = ["Time: %d   Funds: %d   Riders: %d" % (
            gv.get_value("time", 0), gv.get_value("funds", 0), len(riders))]
        for r in riders:
            lines.append(
                "  Rider %d  pos=(%d,%d)  state=%s  speed=%d  orders=%s%s" % (
                    r.rider_id, r.x, r.y, STATE_NAMES.get(r.state, r.state),
                    r.speed, [o.id for o in r.orders],
                    "  [special]" if r.special_case else ""))
        orders = gv.get_value("orders") or []
        waiting = [o.id for o in orders if o.status == "pending"]
        if waiting:
            lines.append("  Unassigned orders: %s" % waiting)
        return "\n".join(lines)

    @staticmethod
    def format_orders(orders):
        """Table of all orders."""
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-6s %-12s %-12s %-6s %-6s %-6s %s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Taken",
            "Rider", "Status")]
        for o in orders:
            taken = o.time_taken
            lines.append("%-4d %-6d %-12s %-12s %-6d %-6s %-6s %s" % (
                o.id, o.start_time, "(%d,%d)" % o.res_pos,
                "(%d,%d)" % o.cus_pos, o.distance,
                "-" if taken is None else str(taken),
                "-" if o.rider_id is None else str(o.rider_id), o.status))
        done = [o for o in orders if o.status == "completed"]
        if done:
            avg = sum(o.time_taken for o in done) / len(done)
            lines.append("Completed: %d   Avg delivery time: %.1f ticks" % (
                len(done), avg))
        return "\n".join(lines)

    @staticmethod
    def format_rider_logs(riders):
        """Every status change of every rider."""
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s %-22s pos=(%s,%s) order=%s" % (
                    e.get("time"), e.get("event"), e.get("x"), e.get("y"),
                    "-" if e.get("order_id") is None else e.get("order_id")))
        return "\n".join(lines)
