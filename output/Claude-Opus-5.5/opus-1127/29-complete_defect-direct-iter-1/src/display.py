"""Status displays and ASCII map visualisation."""

import globalvar
from order_model import STATUS_COMPLETED

CHAR_UNIT = 50
GRID_CHARS = 17


def _cell(v):
    return max(0, min(GRID_CHARS - 1, int(round(int(v) / float(CHAR_UNIT)))))


class DisplayManager:
    """Produces textual output for the CLI."""

    def render_map(self, riders=None, orders=None, route=None, route_start=None):
        """Render the 8x8 grid as ASCII art.

        Each character represents 50 units. Even rows/cols are streets
        ('#'), odd ones are cell interiors ('.'). Route segments are drawn
        with '*', restaurants 'S', customers 'C', riders 'R'.
        """
        if riders is None:
            riders = globalvar.get_value("riders") or []
        if orders is None:
            orders = [o for o in (globalvar.get_value("orders") or [])
                      if o.status != STATUS_COMPLETED]
        grid = [['#' if (r % 2 == 0 or c % 2 == 0) else '.'
                 for c in range(GRID_CHARS)] for r in range(GRID_CHARS)]

        if route:
            pts = list(route)
            if route_start is not None:
                pts = [route_start] + pts
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                c1, r1, c2, r2 = _cell(x1), _cell(y1), _cell(x2), _cell(y2)
                for c in range(min(c1, c2), max(c1, c2) + 1):
                    grid[r1][c] = '*'
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    grid[r][c2] = '*'

        for o in orders:
            grid[_cell(o.res_pos[1])][_cell(o.res_pos[0])] = 'S'
            grid[_cell(o.cus_pos[1])][_cell(o.cus_pos[0])] = 'C'
        for rd in riders:
            grid[_cell(rd.y)][_cell(rd.x)] = 'R'

        header = "      " + " ".join(str(c // 2) if c % 2 == 0 else " "
                                     for c in range(GRID_CHARS))
        lines = [header]
        for r in range(GRID_CHARS):
            label = ("%4d" % (r * CHAR_UNIT)) if r % 2 == 0 else "    "
            lines.append(label + "  " + " ".join(grid[r]))
        lines.append("Legend: R=Rider S=Restaurant C=Customer *=Route "
                     "#=Street .=Block (columns x100 units)")
        return "\n".join(lines)

    def show_status(self):
        """Snapshot of funds and riders."""
        riders = globalvar.get_value("riders") or []
        lines = ["=== System Status (tick %d) ===" % globalvar.get_value("time", 0),
                 "Funds: %d" % globalvar.get_value("funds", 0),
                 "Riders: %d" % len(riders)]
        for r in riders:
            lines.append("  Rider #%d  pos=(%d,%d) speed=%d state=%d (%s) "
                         "orders=%s special=%s delivered=%d" % (
                             r.rider_id, r.x, r.y, r.speed, r.state, r.state_name,
                             [o.id for o in r.orders], r.special_case,
                             r.completed_orders))
        if not riders:
            lines.append("  (no riders yet)")
        return "\n".join(lines)

    def show_orders(self):
        """Details of all orders."""
        orders = globalvar.get_value("orders") or []
        if not orders:
            return "No orders yet."
        lines = ["=== Orders ===",
                 "%-4s %-11s %-6s %-12s %-12s %-6s %-6s %-6s" % (
                     "ID", "Status", "Start", "Restaurant", "Customer",
                     "Dist", "Taken", "Rider")]
        for o in orders:
            lines.append("%-4d %-11s %-6d %-12s %-12s %-6d %-6s %-6s" % (
                o.id, o.status, o.create_time,
                "(%d,%d)" % tuple(o.res_pos), "(%d,%d)" % tuple(o.cus_pos),
                o.distance,
                "-" if o.time_taken is None else str(o.time_taken),
                "-" if o.rider_id is None else "#%d" % o.rider_id))
        return "\n".join(lines)

    def format_event(self, entry):
        """Format a single rider log entry."""
        oid = entry.get("order_id")
        return "[t=%d] Rider #%s %-22s at (%d,%d)%s" % (
            entry.get("time", 0), entry.get("rider_id"), entry.get("event"),
            entry.get("x", 0), entry.get("y", 0),
            "" if oid is None else " order #%d" % oid)

    def show_rider_logs(self):
        """All status changes of all riders."""
        riders = globalvar.get_value("riders") or []
        if not riders:
            return "No riders yet."
        lines = ["=== Rider Activity ==="]
        for r in riders:
            lines.append("Rider #%d:" % r.rider_id)
            for entry in r.log:
                lines.append("  " + self.format_event(entry))
        return "\n".join(lines)

    def show_help(self):
        """Help text."""
        return "\n".join([
            "Commands:",
            "  start (s) [rx ry cx cy]  create an order (coordinates 0-800)",
            "  status (st)              system funds and rider states",
            "  orders (o)               all order details",
            "  riders (r)               rider activity logs",
            "  map (m)                  show the map",
            "  tick (t) [n]             advance the simulation n ticks",
            "  history (hist)           command history ('!!' repeats last)",
            "  save                     save state to JSON",
            "  help (h, ?)              show this help",
            "  quit / exit (q)          exit the program",
        ])
