"""Status display and ASCII map visualisation."""

import globalvar
from path_planner import MAP_SIZE, CELL_SIZE
from rider import RiderState

STEP = CELL_SIZE // 2
POINTS = MAP_SIZE // STEP + 1

LEGEND = ("Legend: + intersection, -/| street, . empty block, R restaurant, "
          "C customer, * route, 0-9 rider (last id digit), @ several riders")


def _idx(v):
    return max(0, min(POINTS - 1, int(round(v / STEP))))


class DisplayManager:
    """Builds textual output for status, orders, logs and maps."""

    def render_map(self, riders=None, orders=None, route_start=None,
                   route=None):
        """Render the 8x8 grid map as ASCII text."""
        riders = riders if riders is not None else globalvar.get_value("riders", [])
        orders = orders if orders is not None else []
        grid = []
        for j in range(POINTS):
            row = []
            for i in range(POINTS):
                x, y = i * STEP, j * STEP
                if x % CELL_SIZE == 0 and y % CELL_SIZE == 0:
                    row.append("+")
                elif x % CELL_SIZE == 0:
                    row.append("|")
                elif y % CELL_SIZE == 0:
                    row.append("-")
                else:
                    row.append(".")
            grid.append(row)

        if route_start is not None and route:
            cur = route_start
            for p in route:
                ci, cj = _idx(cur[0]), _idx(cur[1])
                pi, pj = _idx(p[0]), _idx(p[1])
                di = (pi > ci) - (pi < ci)
                dj = (pj > cj) - (pj < cj)
                grid[cj][ci] = "*"
                while (ci, cj) != (pi, pj):
                    if ci != pi:
                        ci += di
                    else:
                        cj += dj
                    grid[cj][ci] = "*"
                cur = p

        for o in orders:
            grid[_idx(o.res_pos[1])][_idx(o.res_pos[0])] = "R"
            grid[_idx(o.cus_pos[1])][_idx(o.cus_pos[0])] = "C"

        placed = {}
        for r in riders:
            key = (_idx(r.x), _idx(r.y))
            placed[key] = placed.get(key, 0) + 1
            grid[key[1]][key[0]] = "@" if placed[key] > 1 else str(r.rider_id)[-1]

        header = "      " + " ".join(
            str(i * STEP // 100) if (i * STEP) % CELL_SIZE == 0 else " "
            for i in range(POINTS))
        lines = [header + "   (x100)"]
        for j, row in enumerate(grid):
            label = "%4d  " % (j * STEP) if (j * STEP) % CELL_SIZE == 0 else "      "
            lines.append(label + " ".join(row))
        lines.append(LEGEND)
        return "\n".join(lines)

    @staticmethod
    def format_status():
        """Snapshot of funds and every rider's status."""
        riders = globalvar.get_value("riders", []) or []
        lines = [
            "Tick: %d" % globalvar.get_value("tick", 0),
            "Funds: %d" % globalvar.get_value("funds", 0),
            "Riders: %d" % len(riders),
        ]
        for r in riders:
            ids = [o.id for o in r.orders]
            lines.append("  Rider %d at (%d, %d) speed %d - %s, %d order(s) %s%s"
                         % (r.rider_id, r.x, r.y, r.speed,
                            RiderState.name(r.state), len(r.orders), ids,
                            " [special case]" if r.special_case else ""))
        return "\n".join(lines)

    @staticmethod
    def format_orders(orders):
        """Detail table of all orders."""
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-6s %-12s %-12s %-6s %-6s %-6s %-11s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Time",
            "Rider", "Status")]
        for o in orders:
            taken = o.time_taken
            lines.append("%-4d %-6d %-12s %-12s %-6d %-6s %-6s %-11s" % (
                o.id, o.start_time,
                "(%d,%d)" % o.res_pos, "(%d,%d)" % o.cus_pos,
                o.distance, "-" if taken is None else str(taken),
                "-" if o.rider_id is None else str(o.rider_id), o.status))
        return "\n".join(lines)

    @staticmethod
    def format_rider_logs():
        """Every status change of every rider."""
        riders = globalvar.get_value("riders", []) or []
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                order_txt = "" if e.get("order_id") is None else " order #%s" % e["order_id"]
                lines.append("  [t=%s] (%s, %s) %s%s -> %s" % (
                    e.get("time"), e.get("x"), e.get("y"), e["event"],
                    order_txt, RiderState.name(e.get("state", 0))))
        return "\n".join(lines)

    def format_dispatch(self, result):
        """Text for the result of the ``start`` command."""
        order = result["order"]
        rider = result["rider"]
        route = result["route"]
        lines = [
            "Order #%d created." % order.id,
            "Restaurant grid position: (%d, %d)" % order.res_pos,
            "Customer grid position:   (%d, %d)" % order.cus_pos,
            "New rider added: %s" % ("yes" if result["recruited"] else "no"),
            "Funds: %d" % result["funds"],
            "Assigned rider: %d (speed %d units/tick)" % (rider.rider_id, rider.speed),
            "Route: %s" % " -> ".join("(%d,%d)" % tuple(p)
                                      for p in [route.start] + route.waypoints),
            "Route distance: %d units, estimated time: %s ticks"
            % (route.total_distance, route.estimated_time),
        ]
        if result.get("special_case"):
            lines.append("Note: route required a detour (special case).")
        lines.append(self.render_map(globalvar.get_value("riders", []),
                                     [order], route.start, route.waypoints))
        return "\n".join(lines)

    @staticmethod
    def help_text():
        return "\n".join([
            "Commands:",
            "  start (s) [rx ry cx cy]  create an order (coordinates 0-800)",
            "  status (st)              funds and rider status",
            "  orders (o)               order details",
            "  riders (r)               rider status-change log",
            "  map (m)                  show the map",
            "  step (n) [N]             advance simulation N ticks (default 1)",
            "  save                     save state to JSON",
            "  history (hist)           show command history; !! / !N repeat",
            "  help (h, ?)              this help",
            "  quit / exit (q)          exit",
            "Every command advances the simulation by one tick.",
        ])
