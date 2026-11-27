"""Status displays and ASCII map visualisation."""

from grid_map import CELL_SIZE, MAP_SIZE
from rider import STATE_NAMES


class DisplayManager:
    """Builds textual views of the simulation."""

    def __init__(self, map_size=MAP_SIZE, cell_size=CELL_SIZE, resolution=50):
        self.map_size = map_size
        self.cell_size = cell_size
        self.res = resolution
        self.n = map_size // resolution + 1

    def _idx(self, v):
        return max(0, min(self.n - 1, int(round(v / self.res))))

    def render_map(self, riders, orders=None, route=None):
        """Render the map.

        '#' streets, '.' cell interior, 'S' restaurant, 'C' customer,
        'R' rider, '*' planned route.
        """
        step = self.cell_size // self.res
        grid = [["#" if (r % step == 0 or c % step == 0) else "."
                 for c in range(self.n)] for r in range(self.n)]
        if route is not None:
            pts = route.coordinates if hasattr(route, "coordinates") else list(route)
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                ai, aj = self._idx(ax), self._idx(ay)
                bi, bj = self._idx(bx), self._idx(by)
                if ai == bi:
                    for j in range(min(aj, bj), max(aj, bj) + 1):
                        grid[j][ai] = "*"
                elif aj == bj:
                    for i in range(min(ai, bi), max(ai, bi) + 1):
                        grid[aj][i] = "*"
                else:
                    grid[aj][ai] = "*"
                    grid[bj][bi] = "*"
        for order in orders or []:
            if order.status == "completed":
                continue
            if order.status in ("pending", "assigned", "picking_up"):
                grid[self._idx(order.restaurant[1])][self._idx(order.restaurant[0])] = "S"
            grid[self._idx(order.customer[1])][self._idx(order.customer[0])] = "C"
        for rider in riders or []:
            grid[self._idx(rider.y)][self._idx(rider.x)] = "R"

        header = "     " + " ".join(str(i // step) if i % step == 0 else " "
                                    for i in range(self.n))
        lines = [header]
        for j, row in enumerate(grid):
            label = "%3d" % (j * self.res) if j % step == 0 else "   "
            lines.append(label + "  " + " ".join(row))
        lines.append("Legend: R=Rider S=Restaurant C=Customer *=Route "
                     "#=Street .=Block (axis labels x100)")
        return "\n".join(lines)

    @staticmethod
    def format_status(funds, tick, riders, pending_orders=()):
        lines = ["=== System Status (tick %d) ===" % tick,
                 "Funds: %d" % funds,
                 "Riders: %d" % len(riders),
                 "Pending (unassigned) orders: %s" %
                 ([o.id for o in pending_orders] or "none")]
        for r in riders:
            ids = [o.id for o in r.orders if o.status != "completed"]
            lines.append("  Rider %d | pos (%d,%d) | speed %d | state: %s | "
                         "orders: %s | special: %s | delivered: %d"
                         % (r.rider_id, r.x, r.y, r.speed,
                            STATE_NAMES.get(r.state, "?"), ids or "[]",
                            "yes" if r.special_case else "no",
                            r.delivered_count))
        return "\n".join(lines)

    @staticmethod
    def format_orders(orders):
        if not orders:
            return "No orders yet."

        def f(v):
            return "-" if v is None else str(v)

        lines = ["%-4s %-6s %-12s %-12s %-8s %-6s %-6s %-11s %-8s" %
                 ("ID", "Start", "Restaurant", "Customer", "Distance",
                  "Time", "Rider", "Status", "Eff.")]
        for o in orders:
            lines.append("%-4d %-6d %-12s %-12s %-8d %-6s %-6s %-11s %-8s" %
                         (o.id, o.start_time, "(%d,%d)" % o.restaurant,
                          "(%d,%d)" % o.customer, o.distance, f(o.time_taken),
                          f(o.rider_id), o.status, f(o.efficiency)))
        return "\n".join(lines)

    @staticmethod
    def format_rider_logs(riders):
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider %d (distance travelled %d, delivered %d):"
                         % (r.rider_id, r.distance_travelled, r.delivered_count))
            for e in r.log:
                order_txt = "" if e.get("order_id") is None else \
                    " order #%s" % e["order_id"]
                lines.append("  t=%-5s (%d,%d) %-22s%s -> %s" %
                             (e.get("time"), e.get("x", 0), e.get("y", 0),
                              e.get("event"), order_txt,
                              STATE_NAMES.get(e.get("state"), "?")))
        return "\n".join(lines)

    @staticmethod
    def format_route(rider, route):
        pts = " -> ".join("(%d,%d)" % p for p in route.coordinates)
        return ("Rider %d route | speed %d units/tick | distance %d | "
                "estimated time %d ticks\n  %s"
                % (rider.rider_id, rider.speed, route.total_distance,
                   route.estimated_time, pts))
