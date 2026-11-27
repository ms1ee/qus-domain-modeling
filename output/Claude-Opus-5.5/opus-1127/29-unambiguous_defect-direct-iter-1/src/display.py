"""Status display and ASCII map visualization."""

import globalvar
from config import CELL_SIZE, MAP_SIZE
from rider import STATE_NAMES

STEP = CELL_SIZE // 2
LEGEND = ("Legend: 0-9/A-Z rider  R restaurant  C customer  * route  "
          "+ intersection  -,| street  . empty cell")


def _snap(v):
    return int(round(v / STEP)) * STEP


def expand_route(points):
    """Expand a list of waypoints into points every 50 units."""
    result = []
    if not points:
        return result
    cx, cy = _snap(points[0][0]), _snap(points[0][1])
    result.append((cx, cy))
    for p in points[1:]:
        tx, ty = _snap(p[0]), _snap(p[1])
        while cx != tx:
            cx += STEP if tx > cx else -STEP
            result.append((cx, cy))
        while cy != ty:
            cy += STEP if ty > cy else -STEP
            result.append((cx, cy))
    return result


def rider_symbol(rider_id):
    """Single character symbol for a rider."""
    rid = int(rider_id)
    if rid < 10:
        return str(rid)
    if rid < 36:
        return chr(ord("A") + rid - 10)
    return "@"


class DisplayManager:
    """Formats status information and renders the ASCII map."""

    def render_map(self, route=None, show_orders=True, orders=None):
        """Render the 8x8 grid map (at 50-unit resolution) as a string."""
        n = MAP_SIZE // STEP + 1
        grid = {}
        for i in range(n):
            for j in range(n):
                x, y = i * STEP, j * STEP
                if x % CELL_SIZE == 0 and y % CELL_SIZE == 0:
                    ch = "+"
                elif y % CELL_SIZE == 0:
                    ch = "-"
                elif x % CELL_SIZE == 0:
                    ch = "|"
                else:
                    ch = "."
                grid[(x, y)] = ch
        if route:
            for p in expand_route(route):
                if p in grid:
                    grid[p] = "*"
        if orders is None and show_orders:
            orders = [o for o in (globalvar.get_value("orders") or [])
                      if o.status != "completed"]
        for o in orders or []:
            grid[tuple(o.res_pos)] = "R"
            grid[tuple(o.cus_pos)] = "C"
        for r in globalvar.get_value("riders") or []:
            p = (_snap(r.x), _snap(r.y))
            if p in grid:
                grid[p] = rider_symbol(r.rider_id)
        lines = []
        for j in range(n - 1, -1, -1):
            y = j * STEP
            row = " ".join(grid[(i * STEP, y)] for i in range(n))
            lines.append("%4d %s" % (y, row))
        footer = "     " + " ".join(
            str(i * STEP // 100) if (i * STEP) % CELL_SIZE == 0 else " "
            for i in range(n))
        lines.append(footer + "   (x100)")
        lines.append(LEGEND)
        return "\n".join(lines)

    def status_text(self):
        """Snapshot of funds, time and every rider."""
        riders = globalvar.get_value("riders") or []
        pending = globalvar.get_value("pending_orders") or []
        lines = [
            "Time: %s" % globalvar.get_value("time", 0),
            "Funds: %s" % globalvar.get_value("funds", 0),
            "Riders: %d" % len(riders),
            "Pending orders: %d" % len(pending),
        ]
        for r in riders:
            ids = [str(getattr(o, "id", "?")) for o in r.orders]
            lines.append(
                "  Rider %s at (%s, %s) speed %s - %s, %d order(s) [%s]%s" % (
                    r.rider_id, r.x, r.y, r.speed,
                    STATE_NAMES.get(r.state, "unknown"), len(r.orders),
                    ", ".join(ids), " (special case)" if r.special_case else ""))
        return "\n".join(lines)

    def orders_text(self):
        """Table with every order."""
        orders = globalvar.get_value("orders") or []
        if not orders:
            return "No orders yet."
        header = "%-4s %-6s %-12s %-12s %-6s %-7s %-6s %-11s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Taken",
            "Rider", "Status")
        lines = [header, "-" * len(header)]
        for o in orders:
            lines.append("%-4s %-6s %-12s %-12s %-6s %-7s %-6s %-11s" % (
                o.id, o.created_time,
                "(%d,%d)" % tuple(o.res_pos), "(%d,%d)" % tuple(o.cus_pos),
                o.route_distance,
                "-" if o.time_taken is None else o.time_taken,
                "-" if o.rider_id is None else o.rider_id, o.status))
        return "\n".join(lines)

    def riders_text(self):
        """Every status change of every rider."""
        riders = globalvar.get_value("riders") or []
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider %s:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s %-22s at (%s, %s)%s" % (
                    e.get("time"), e.get("event"), e.get("x"), e.get("y"),
                    "" if e.get("order_id") is None
                    else "  order #%s" % e.get("order_id")))
        return "\n".join(lines)

    def order_result_text(self, result):
        """Text describing the result of a ``start`` command."""
        order = result["order"]
        rider = result["rider"]
        new_rider = result["new_rider"]
        lines = [
            "Order #%s created." % order.id,
            "  Restaurant grid position: (%d, %d)" % tuple(order.res_pos),
            "  Customer grid position:   (%d, %d)" % tuple(order.cus_pos),
            "  New rider added: %s" % (
                "Yes (rider %s)" % new_rider.rider_id if new_rider else "No"),
        ]
        if rider is None:
            lines.append("  No rider available (insufficient funds); "
                         "order is pending.")
            return "\n".join(lines)
        lines.append("  Assigned rider: %s (speed %s units/tick)" % (
            rider.rider_id, rider.speed))
        lines.append("  Route length: %s units, estimated time: %s ticks" % (
            result["route_length"], result["eta"]))
        route = result["route"]
        lines.append("  Route: " + " -> ".join(
            "(%d,%d)" % (p[0], p[1]) for p in route))
        lines.append(self.render_map(route=route, orders=[order]))
        return "\n".join(lines)
