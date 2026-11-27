"""Status display and ASCII map visualisation."""

from path_planner import PathPlanner
from rider import STATE_NAMES

SCALE = 50
N = 800 // SCALE + 1  # 17 character positions per axis

EVENT_NAMES = {
    "spawn": "spawned",
    "accepted_order": "accepted order",
    "arrived_at_merchant": "arrived at restaurant",
    "delivered_to_customer": "delivered to customer",
}


def _idx(v):
    return max(0, min(N - 1, int(round(v / SCALE))))


class DisplayManager:
    """Formats status information and maps as text."""

    LEGEND = ("Legend: '+' intersection  '-' '|' street  '.' empty cell  "
              "'R' restaurant  'C' customer  '*' route  digit/'@' rider")

    def render_map(self, riders, orders=(), route=None, highlight=None):
        """Return an ASCII map string.

        ``route`` is an optional polyline drawn with '*'.
        """
        grid = []
        for r in range(N):
            row = []
            for c in range(N):
                if r % 2 == 0 and c % 2 == 0:
                    row.append("+")
                elif r % 2 == 0:
                    row.append("-")
                elif c % 2 == 0:
                    row.append("|")
                else:
                    row.append(".")
            grid.append(row)
        if route:
            for x, y in PathPlanner.sample_polyline(route):
                grid[_idx(y)][_idx(x)] = "*"
        for o in orders:
            if o.status == "completed":
                continue
            rx, ry = o.res_pos
            cx, cy = o.cus_pos
            grid[_idx(ry)][_idx(rx)] = "R"
            grid[_idx(cy)][_idx(cx)] = "C"
        for rd in riders:
            if highlight is not None and rd.rider_id == highlight:
                sym = "@"
            else:
                sym = str(rd.rider_id % 10)
            grid[_idx(rd.y)][_idx(rd.x)] = sym
        lines = ["     " + "".join(("%-4d" % (c * SCALE)) if c % 2 == 0
                                   else "" for c in range(N))]
        for r, row in enumerate(grid):
            label = "%4d " % (r * SCALE) if r % 2 == 0 else "     "
            lines.append(label + " ".join(row))
        lines.append(self.LEGEND)
        return "\n".join(lines)

    @staticmethod
    def format_status(manager):
        lines = ["=== System status (tick %d) ===" % manager.time,
                 "Funds: %d" % manager.funds,
                 "Riders: %d" % len(manager.riders)]
        for r in manager.riders:
            ids = [o.id for o in r.orders]
            lines.append("  Rider #%d at (%d,%d) speed=%d state=%s orders=%d %s"
                         % (r.rider_id, r.x, r.y, r.speed,
                            STATE_NAMES.get(r.state, "?"), len(r.orders),
                            ids))
        return "\n".join(lines)

    @staticmethod
    def format_orders(orders):
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-6s %-11s %-11s %-6s %-6s %-11s %-5s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Time",
            "Status", "Rider")]
        for o in orders:
            taken = o.time_taken
            lines.append("%-4d %-6d %-11s %-11s %-6d %-6s %-11s %-5s" % (
                o.id, o.create_time, "(%d,%d)" % o.res_pos,
                "(%d,%d)" % o.cus_pos, o.distance,
                "-" if taken is None else str(taken), o.status,
                "-" if o.rider_id is None else str(o.rider_id)))
        return "\n".join(lines)

    @staticmethod
    def format_rider_logs(riders):
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider #%d:" % r.rider_id)
            for e in r.log:
                desc = EVENT_NAMES.get(e["event"], e["event"])
                order_txt = ("" if e.get("order_id") is None
                             else " order #%s" % e["order_id"])
                lines.append("  t=%-5s %-22s%s at (%s,%s)" % (
                    e.get("time"), desc, order_txt, e.get("x"), e.get("y")))
        return "\n".join(lines)

    @staticmethod
    def format_help():
        return "\n".join([
            "Commands:",
            "  start|s [rx ry cx cy]  create an order (coordinates 0-800)",
            "  status|st              system funds and rider states",
            "  orders|o               all order details",
            "  riders|r               rider status change history",
            "  map|m                  show the current map",
            "  tick|t|wait [n]        advance the simulation n ticks",
            "  history                show command history",
            "  save [file]            save state to JSON",
            "  help|h                 this help",
            "  quit|exit|q            exit",
            "Every command advances the simulation by one tick.",
        ])
