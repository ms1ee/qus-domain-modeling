"""Status displays and ASCII map visualisation."""

from path_planner import PathPlanner, MAP_SIZE
from rider import STATE_NAMES

HALF = 50
DIM = MAP_SIZE // HALF + 1  # 17 characters: streets on even indices


def _idx(v):
    return max(0, min(DIM - 1, int(round(v / HALF))))


class DisplayManager:
    """Builds text for status, order, rider-log and map displays."""

    @staticmethod
    def _base_grid():
        grid = []
        for row in range(DIM):
            line = []
            for col in range(DIM):
                line.append("#" if row % 2 == 0 or col % 2 == 0 else ".")
            grid.append(line)
        return grid

    @staticmethod
    def _draw_route(grid, points):
        for a, b in zip(points, points[1:]):
            ax, ay, bx, by = _idx(a[0]), _idx(a[1]), _idx(b[0]), _idx(b[1])
            step = 1 if bx >= ax else -1
            for c in range(ax, bx + step, step):
                grid[ay][c] = "*"
            step = 1 if by >= ay else -1
            for r in range(ay, by + step, step):
                grid[r][bx] = "*"

    def render_map(self, riders=(), orders=(), routes=()):
        """Render the 8x8 grid (streets '#', cells '.', route '*').

        'S' marks restaurants and 'C' customers of open orders, 'R' riders.
        """
        grid = self._base_grid()
        for route in routes:
            if route:
                self._draw_route(grid, route)
        for o in orders:
            if o.status == "completed":
                continue
            if o.status in ("pending", "assigned", "picking_up"):
                grid[_idx(o.res_pos[1])][_idx(o.res_pos[0])] = "S"
            grid[_idx(o.cus_pos[1])][_idx(o.cus_pos[0])] = "C"
        for r in riders:
            grid[_idx(r.y)][_idx(r.x)] = "R"
        lines = ["     " + " ".join(str((c * HALF) // 100 % 10) if c % 2 == 0
                                    else " " for c in range(DIM))]
        for row in range(DIM):
            label = "%3d " % (row * HALF) if row % 2 == 0 else "    "
            lines.append(label + " " + " ".join(grid[row]))
        lines.append("Legend: R=rider S=restaurant C=customer *=route "
                     "#=street .=empty (x axis in hundreds, y grows downward)")
        return "\n".join(lines)

    def format_dispatch(self, result):
        """Describe the outcome of a ``start`` command."""
        order = result["order"]
        lines = ["Order #%d created." % order.id,
                 "  Restaurant grid position: (%d, %d)" % order.res_pos,
                 "  Customer grid position:   (%d, %d)" % order.cus_pos]
        new = result.get("new_riders") or []
        if new:
            lines.append("  New rider added: yes (ID %s)"
                         % ", ".join(str(r.rider_id) for r in new))
        else:
            lines.append("  New rider added: no")
        rider = result.get("rider")
        if rider is None:
            lines.append("  No rider available - order is pending.")
            return "\n".join(lines)
        length = result.get("route_length", 0)
        speed = rider.speed if rider.speed > 0 else 1
        eta = -(-length // speed)
        lines.append("  Assigned rider: %d at (%d, %d)" % (rider.rider_id,
                                                           rider.x, rider.y))
        lines.append("  Route: " + " -> ".join("(%d,%d)" % p
                                               for p in result["route"]))
        lines.append("  Speed: %d units/tick, distance: %d units, "
                     "estimated time: %d ticks" % (speed, length, eta))
        lines.append(self.render_map([rider], [order] + rider.open_orders(),
                                     [result["route"]]))
        return "\n".join(lines)

    @staticmethod
    def format_status(system):
        """Snapshot of funds, time and every rider."""
        riders = system.riders
        lines = ["Time: %d   Funds: %d   Riders: %d"
                 % (system.time, system.funds, len(riders))]
        if not riders:
            lines.append("  (no riders)")
        for r in riders:
            lines.append("  Rider %d: pos=(%d, %d) state=%s orders=%d %s%s"
                         % (r.rider_id, r.x, r.y,
                            STATE_NAMES.get(r.state, "?"), len(r.orders),
                            [o.id for o in r.orders],
                            " [special case]" if r.special_case else ""))
        pending = system.order_manager.pending_orders()
        if pending:
            lines.append("  Pending (unassigned) orders: %s"
                         % [o.id for o in pending])
        return "\n".join(lines)

    @staticmethod
    def format_orders(orders):
        """Table with details of every order."""
        if not orders:
            return "No orders."
        header = ("%-4s %-7s %-12s %-12s %-6s %-6s %-6s %-11s"
                  % ("ID", "Start", "Restaurant", "Customer", "Dist",
                     "Taken", "Rider", "Status"))
        lines = [header, "-" * len(header)]
        for o in orders:
            taken = o.time_taken
            lines.append("%-4d %-7d %-12s %-12s %-6d %-6s %-6s %-11s"
                         % (o.id, o.created_time,
                            "(%d,%d)" % tuple(o.res_pos),
                            "(%d,%d)" % tuple(o.cus_pos), o.distance,
                            "-" if taken is None else taken,
                            "-" if o.rider_id is None else o.rider_id,
                            o.status))
        return "\n".join(lines)

    @staticmethod
    def format_rider_logs(riders):
        """Every recorded status change of every rider."""
        if not riders:
            return "No riders."
        lines = []
        for r in riders:
            lines.append("Rider %d (delivered %d, travelled %d units):"
                         % (r.rider_id, r.delivered_count, r.distance_traveled))
            for e in r.log:
                lines.append("  t=%-5s %-22s pos=(%s, %s) order=%s"
                             % (e.get("time"), e.get("event"), e.get("x"),
                                e.get("y"),
                                "-" if e.get("order_id") is None
                                else e.get("order_id")))
        return "\n".join(lines)
