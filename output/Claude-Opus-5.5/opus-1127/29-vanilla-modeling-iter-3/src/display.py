"""Status display and ASCII map visualisation."""

import globalvar
from path_planner import PathPlanner
from rider import RiderState

GRID_CHARS = 17  # 8 cells + 9 street lines
UNIT = 50


def _idx(v):
    i = int(v / float(UNIT) + 0.5)
    return max(0, min(GRID_CHARS - 1, i))


class DisplayManager:
    """Builds textual views of the system state."""

    def status_text(self):
        riders = globalvar.get_value("riders", []) or []
        lines = ["=== System Status (tick %s) ===" % globalvar.get_value("tick", 0),
                 "Funds : %s" % globalvar.get_value("funds", 0),
                 "Riders: %d" % len(riders)]
        if riders:
            lines.append("%-4s %-12s %-6s %-12s %s" %
                         ("ID", "Position", "Speed", "State", "Orders"))
            for r in riders:
                lines.append("%-4s %-12s %-6s %-12s %d %s" % (
                    r.rider_id, "(%d,%d)" % (r.x, r.y), r.speed,
                    RiderState.name(r.state), len(r.orders),
                    [getattr(o, "id", "?") for o in r.orders]))
        return "\n".join(lines)

    def orders_text(self):
        orders = globalvar.get_value("orders", []) or []
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-6s %-11s %-11s %-9s %-6s %-6s %s" % (
            "ID", "Start", "Restaurant", "Customer", "Distance", "Taken",
            "Rider", "Status")]
        for o in orders:
            lines.append("%-4s %-6s %-11s %-11s %-9s %-6s %-6s %s" % (
                o.id, o.start_time, "(%d,%d)" % o.res_pos,
                "(%d,%d)" % o.cus_pos, o.distance,
                "-" if o.time_taken is None else o.time_taken,
                "-" if o.rider_id is None else o.rider_id, o.status))
        return "\n".join(lines)

    def riders_text(self, rider_id=None):
        riders = globalvar.get_value("riders", []) or []
        if rider_id is not None:
            riders = [r for r in riders if r.rider_id == rider_id]
        if not riders:
            return "No riders."
        lines = []
        for r in riders:
            lines.append("Rider %s (now %s at (%d,%d))" %
                         (r.rider_id, RiderState.name(r.state), r.x, r.y))
            for e in r.log:
                oid = e.get("order_id")
                lines.append("  [t=%s] %-22s at (%s,%s)%s" % (
                    e.get("time"), e.get("event"), e.get("x"), e.get("y"),
                    "" if oid is None else " order #%s" % oid))
        return "\n".join(lines)

    def render_map(self, route=None):
        """Render an ASCII map; optionally overlay a Route with '*'."""
        grid = [['#' if (r % 2 == 0 or c % 2 == 0) else '.'
                 for c in range(GRID_CHARS)] for r in range(GRID_CHARS)]

        def put(x, y, ch):
            grid[_idx(y)][_idx(x)] = ch

        if route is not None:
            wps = route.waypoints
            for a, b in zip(wps, wps[1:]):
                for p in PathPlanner.segment_points(a, b, UNIT / 2.0):
                    put(p[0], p[1], '*')
        for o in globalvar.get_value("orders", []) or []:
            if o.status == "completed":
                continue
            put(o.res_pos[0], o.res_pos[1], 'S')
            put(o.cus_pos[0], o.cus_pos[1], 'C')
        for r in globalvar.get_value("riders", []) or []:
            put(r.x, r.y, 'R')
        header = "      " + " ".join(str(c // 2 * 100 // 100) if c % 2 == 0 else ' '
                                     for c in range(GRID_CHARS))
        lines = ["x-lines (x100):", header]
        for ri, row in enumerate(grid):
            label = str(ri * UNIT) if ri % 2 == 0 else ""
            lines.append("%5s " % label + " ".join(row))
        lines.append("Legend: R=Rider S=Restaurant C=Customer *=Route "
                     "#=Street .=Empty (y grows downward)")
        return "\n".join(lines)
