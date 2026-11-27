"""Status display and ASCII map visualisation."""

from path_planner import DEFAULT_GRID
from rider import STATE_NAMES

HELP_TEXT = """Commands (shortcut):
  start (s) [rx ry cx cy]  create an order (coordinates 0-800)
  status (st)              funds, riders and map
  orders (o)               all order details
  riders (r)               rider status-change logs
  map (m)                  show ASCII map
  step (n) [N]             advance simulation N ticks (default 1)
  history (hi)             show command history; !N re-runs command N
  save                     save state to JSON
  help (h, ?)              this help
  quit / exit (q)          exit the program
Every command also advances the simulation by one tick."""

LEGEND = ("Legend: digit=rider (id%10), @=several riders, R=restaurant, "
          "C=customer, *=route, +=crossing, -|=street, .=block")


class DisplayManager:
    """Formats status information and renders the ASCII map."""

    STEP = 50

    def __init__(self, grid=None):
        self.grid = grid or DEFAULT_GRID

    def _idx(self, v):
        n = self.grid.map_size // self.STEP
        return max(0, min(n, int(round(v / float(self.STEP)))))

    def render_map(self, riders, orders=None, route=None):
        """Render an ASCII map (y grows downwards).

        :param riders: riders to draw.
        :param orders: orders whose restaurant/customer are drawn.
        :param route: optional list of waypoints drawn as '*'.
        """
        cs = self.grid.cell_size
        n = self.grid.map_size // self.STEP + 1
        cells = []
        for r in range(n):
            row = []
            for c in range(n):
                x, y = c * self.STEP, r * self.STEP
                if x % cs == 0 and y % cs == 0:
                    row.append("+")
                elif x % cs == 0:
                    row.append("|")
                elif y % cs == 0:
                    row.append("-")
                else:
                    row.append(".")
            cells.append(row)
        if route:
            for i in range(len(route) - 1):
                (x1, y1), (x2, y2) = route[i], route[i + 1]
                c1, r1, c2, r2 = (self._idx(x1), self._idx(y1),
                                  self._idx(x2), self._idx(y2))
                if r1 == r2:
                    for c in range(min(c1, c2), max(c1, c2) + 1):
                        cells[r1][c] = "*"
                else:
                    for r in range(min(r1, r2), max(r1, r2) + 1):
                        cells[r][c1] = "*"
        for o in orders or []:
            cells[self._idx(o.res_pos[1])][self._idx(o.res_pos[0])] = "R"
            cells[self._idx(o.cus_pos[1])][self._idx(o.cus_pos[0])] = "C"
        seen = {}
        for rd in riders or []:
            key = (self._idx(rd.y), self._idx(rd.x))
            seen[key] = seen.get(key, 0) + 1
            cells[key[0]][key[1]] = ("@" if seen[key] > 1
                                     else str(rd.rider_id % 10))
        header = "x/100 " + " ".join(
            str(c // 2) if c % 2 == 0 else " " for c in range(n))
        lines = [header]
        for r in range(n):
            lines.append("%5d " % (r * self.STEP) + " ".join(cells[r]))
        lines.append(LEGEND)
        return "\n".join(lines)

    def format_status(self, funds, tick, riders, orders):
        """System snapshot: funds, riders and map."""
        lines = ["=== System status (tick %d) ===" % tick,
                 "Funds: %d" % funds,
                 "Riders: %d" % len(riders)]
        for r in riders:
            ids = ", ".join("#%d" % o.id for o in r.orders) or "-"
            lines.append(
                "  Rider %d at (%d,%d) | %s | speed %d | orders: %s%s" % (
                    r.rider_id, r.x, r.y, STATE_NAMES.get(int(r.state), "?"),
                    r.speed, ids, " | special" if r.special_case else ""))
        active = [o for o in orders if not o.completed]
        lines.append(self.render_map(riders, active))
        return "\n".join(lines)

    def format_orders(self, orders):
        """Table of all orders."""
        if not orders:
            return "No orders yet."
        lines = ["%-5s %-6s %-11s %-11s %-8s %-6s %-6s %s" % (
            "ID", "Start", "Restaurant", "Customer", "Distance",
            "Time", "Rider", "Status")]
        for o in orders:
            lines.append("%-5s %-6d %-11s %-11s %-8d %-6s %-6s %s" % (
                "#%d" % o.id, o.start_time,
                "(%d,%d)" % o.res_pos, "(%d,%d)" % o.cus_pos,
                o.distance,
                "-" if o.time_taken is None else str(o.time_taken),
                "-" if o.rider_id is None else str(o.rider_id),
                o.status))
        return "\n".join(lines)

    def format_rider_logs(self, riders):
        """Every rider status change."""
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-4d %-22s at (%d,%d) order %s -> %s" % (
                    e.get("time", 0), e.get("event"), e.get("x", 0),
                    e.get("y", 0),
                    "-" if e.get("order_id") is None else "#%d" % e["order_id"],
                    STATE_NAMES.get(e.get("state", 0), "?")))
        return "\n".join(lines)

    def format_start_result(self, result, funds):
        """Output of the ``start`` command."""
        o = result["order"]
        r = result["rider"]
        route = result["route"]
        g = self.grid
        lines = [
            "Order #%d created at tick %d" % (o.id, o.start_time),
            "  Restaurant: input (%d,%d) -> grid (%d,%d), cell (%d,%d)" % (
                o.raw_res_pos + o.res_pos + (g.to_grid_cell(o.res_pos[0]),
                                             g.to_grid_cell(o.res_pos[1]))),
            "  Customer:   input (%d,%d) -> grid (%d,%d), cell (%d,%d)" % (
                o.raw_cus_pos + o.cus_pos + (g.to_grid_cell(o.cus_pos[0]),
                                             g.to_grid_cell(o.cus_pos[1]))),
            "  New rider added: %s (funds: %d)" % (
                "yes" if result["recruited"] else "no", funds),
            "  Assigned rider %d at (%d,%d), speed %d units/tick, "
            "queue position %d" % (r.rider_id, r.x, r.y, r.speed,
                                   result["queue_position"]),
            "  Route: " + " -> ".join("(%d,%d)" % p for p in route.waypoints),
            "  Distance: %d units, estimated time: %d ticks" % (
                route.length, route.estimated_time),
            self.render_map([r], [o], route.waypoints),
        ]
        return "\n".join(lines)

    @staticmethod
    def help_text():
        """Command help."""
        return HELP_TEXT
