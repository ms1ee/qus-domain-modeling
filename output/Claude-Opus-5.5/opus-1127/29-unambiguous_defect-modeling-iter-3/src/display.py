"""Status displays and ASCII map rendering."""

from grid_map import CELL_SIZE, MAP_SIZE
from rider import RiderState

STEP = CELL_SIZE // 2
N = MAP_SIZE // STEP + 1

LEGEND = ("Legend: + intersection, -/| street, . location, * route, "
          "R restaurant, C customer, digit = rider id (last digit), "
          "@ several riders. Axis labels in hundreds; y grows downward.")


class DisplayManager:
    """Builds textual views of the simulation state."""

    @staticmethod
    def _idx(v):
        return max(0, min(N - 1, int(round(v / STEP))))

    def _base(self):
        canvas = []
        for j in range(N):
            row = []
            for i in range(N):
                x, y = i * STEP, j * STEP
                if x % CELL_SIZE == 0 and y % CELL_SIZE == 0:
                    row.append("+")
                elif y % CELL_SIZE == 0:
                    row.append("-")
                elif x % CELL_SIZE == 0:
                    row.append("|")
                else:
                    row.append(".")
            canvas.append(row)
        return canvas

    def _draw_path(self, canvas, start, waypoints):
        prev = start
        for p in waypoints:
            x0, y0 = self._idx(prev[0]), self._idx(prev[1])
            x1, y1 = self._idx(p[0]), self._idx(p[1])
            if x0 != x1:
                for i in range(min(x0, x1), max(x0, x1) + 1):
                    canvas[y0][i] = "*"
            if y0 != y1:
                for j in range(min(y0, y1), max(y0, y1) + 1):
                    canvas[j][x1] = "*"
            canvas[y1][x1] = "*"
            prev = p

    def render_map(self, riders, orders=(), routes=()):
        """Render the map. ``routes`` is an iterable of (start, waypoints)."""
        canvas = self._base()
        for start, wps in routes:
            self._draw_path(canvas, start, wps)
        for o in orders:
            if o.status == "completed":
                continue
            canvas[self._idx(o.res_y)][self._idx(o.res_x)] = "R"
            canvas[self._idx(o.cus_y)][self._idx(o.cus_x)] = "C"
        placed = {}
        for r in riders:
            key = (self._idx(r.x), self._idx(r.y))
            placed[key] = "@" if key in placed else str(r.rider_id % 10)
        for (i, j), ch in placed.items():
            canvas[j][i] = ch
        header = "    " + " ".join(str(i // 2) if i % 2 == 0 else " "
                                   for i in range(N))
        lines = [header]
        for j, row in enumerate(canvas):
            label = str(j // 2) if j % 2 == 0 else " "
            lines.append(" %s  %s" % (label, " ".join(row)))
        lines.append(LEGEND)
        return "\n".join(lines)

    @staticmethod
    def format_status(funds, tick, riders):
        lines = ["=== System Status (tick %d) ===" % tick,
                 "Funds: %d" % funds,
                 "Riders: %d" % len(riders)]
        if not riders:
            lines.append("  (no riders yet)")
        for r in riders:
            ids = [o.id for o in r.orders]
            lines.append(
                "  Rider %-3d pos=(%3d,%3d) speed=%d state=%-11s orders=%d %s%s"
                % (r.rider_id, r.x, r.y, r.speed, RiderState.name(r.state),
                   len(r.orders), ids, " [special case]" if r.special_case else ""))
        return "\n".join(lines)

    @staticmethod
    def format_orders(orders, history=()):
        lines = ["=== Orders ==="]
        if not orders and not history:
            lines.append("  (no orders)")
            return "\n".join(lines)
        lines.append("  %-4s %-6s %-11s %-11s %-8s %-6s %-6s %-11s %s" % (
            "ID", "Start", "Restaurant", "Customer", "Distance", "Taken",
            "Rider", "Status", "Eff."))
        for h in history:
            lines.append("  %-4s %-6s %-11s %-11s %-8s %-6s %-6s %-11s %s" % (
                h.get("id"), h.get("start_time"),
                "(%s,%s)" % tuple(h.get("restaurant", ["?", "?"])),
                "(%s,%s)" % tuple(h.get("customer", ["?", "?"])),
                h.get("distance"), h.get("time_taken") if h.get("time_taken")
                is not None else "-", h.get("rider_id"),
                str(h.get("status")) + "*", "-"))
        for o in orders:
            eff = o.efficiency()
            lines.append("  %-4d %-6d %-11s %-11s %-8d %-6s %-6s %-11s %s" % (
                o.id, o.start_time, "(%d,%d)" % o.res_pos, "(%d,%d)" % o.cus_pos,
                o.distance, o.time_taken if o.time_taken is not None else "-",
                o.rider_id if o.rider_id is not None else "-", o.status,
                eff if eff is not None else "-"))
        if history:
            lines.append("  (* archived from a previous session)")
        return "\n".join(lines)

    @staticmethod
    def format_rider_logs(riders):
        lines = ["=== Rider Status History ==="]
        if not riders:
            lines.append("  (no riders)")
        for r in riders:
            lines.append("Rider %d (travelled %d units, completed %s):"
                         % (r.rider_id, r.distance_travelled, r.completed_orders))
            for e in r.log:
                order = "order #%s" % e["order_id"] if e["order_id"] is not None else "-"
                lines.append("  t=%-5d %-22s %-10s at (%3d,%3d) -> %s" % (
                    e["time"], e["event"], order, e["x"], e["y"],
                    RiderState.name(e["state"])))
        return "\n".join(lines)

    def format_route_info(self, order, rider, new_rider, route, wait_distance,
                          riders, orders):
        lines = ["Order #%d created." % order.id,
                 "Restaurant grid position: (%d, %d)  [input (%d, %d)]"
                 % (order.res_x, order.res_y, order.raw_res[0], order.raw_res[1]),
                 "Customer grid position:   (%d, %d)  [input (%d, %d)]"
                 % (order.cus_x, order.cus_y, order.raw_cus[0], order.raw_cus[1]),
                 "New rider added: %s" % ("yes" if new_rider else "no")]
        if rider is None:
            lines.append("No rider available (insufficient funds). "
                         "The order will be assigned when possible.")
            return "\n".join(lines)
        total = wait_distance + route.distance
        eta = -(-total // rider.speed)
        lines.append("Assigned rider: %d  speed: %d units/tick" % (rider.rider_id, rider.speed))
        if wait_distance:
            lines.append("Rider has queued work: %d units before this order"
                         % wait_distance)
        lines.append("Route: (%d,%d) -> " % route.start + " -> ".join(
            "(%d,%d)" % p for p in route.waypoints) if route.waypoints
            else "Route: rider is already in place")
        lines.append("Route distance: %d units, estimated time: %d ticks"
                     % (route.distance, eta))
        lines.append(self.render_map(riders, [order], [(route.start, route.waypoints)]))
        return "\n".join(lines)

    @staticmethod
    def help_text():
        return "\n".join([
            "Commands (shortcut):",
            "  start (n,1) [rx ry cx cy]  create an order",
            "  status (s,2)               system funds and riders",
            "  orders (o,3)               all orders",
            "  riders (r,4)               rider status history",
            "  map (m)                    show the map",
            "  tick (t) [n]               advance n ticks",
            "  run [max]                  advance until all riders are idle",
            "  save                       save state to JSON",
            "  history (h)                command history (!! or !n to repeat)",
            "  help (?)                   this help",
            "  quit / exit (q)            exit the program",
            "Each command loop iteration advances the simulation by one tick.",
        ])
