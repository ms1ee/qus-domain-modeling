"""Status display and ASCII map visualisation."""

import globalvar
from path_planner import MAP_SIZE
from rider import STATE_NAMES

CELL = 50
N = MAP_SIZE // CELL + 1  # 17 characters per side


def _idx(v):
    return max(0, min(N - 1, int(round(v / CELL))))


class DisplayManager:
    """Formats system information for the command line."""

    def render_map(self, riders=None, orders=None, routes=None):
        """Return an ASCII map string.

        Each character represents 50 units; '#' are streets, '.' blocks,
        'S' restaurants, 'C' customers, 'R' riders and '-', '|', '+' routes.
        """
        canvas = [['#' if r % 2 == 0 or c % 2 == 0 else '.'
                   for c in range(N)] for r in range(N)]
        for route in routes or []:
            for a, b in zip(route, route[1:]):
                self._draw_segment(canvas, a, b)
            for p in route[1:-1]:
                canvas[_idx(p[1])][_idx(p[0])] = '+'
        for o in orders or []:
            if o.status == "completed":
                continue
            canvas[_idx(o.res_pos[1])][_idx(o.res_pos[0])] = 'S'
            canvas[_idx(o.cus_pos[1])][_idx(o.cus_pos[0])] = 'C'
        for r in riders or []:
            canvas[_idx(r.y)][_idx(r.x)] = 'R'
        header = "     " + " ".join(
            str(c // 2) if c % 2 == 1 else " " for c in range(N))
        lines = [header]
        for r, row in enumerate(canvas):
            label = "%3d " % (r * CELL) if r % 2 == 0 else "  %d " % (r // 2)
            lines.append(label + " " + " ".join(row))
        lines.append("Legend: R=rider S=restaurant C=customer #=street "
                     ".=block, route: - | +  (1 char = 50 units)")
        return "\n".join(lines)

    @staticmethod
    def _draw_segment(canvas, a, b):
        r1, c1 = _idx(a[1]), _idx(a[0])
        r2, c2 = _idx(b[1]), _idx(b[0])
        if r1 == r2:
            for c in range(min(c1, c2), max(c1, c2) + 1):
                canvas[r1][c] = '-'
        elif c1 == c2:
            for r in range(min(r1, r2), max(r1, r2) + 1):
                canvas[r][c1] = '|'
        else:
            for c in range(min(c1, c2), max(c1, c2) + 1):
                canvas[r1][c] = '-'
            for r in range(min(r1, r2), max(r1, r2) + 1):
                canvas[r][c2] = '|'

    def current_map(self):
        riders = globalvar.get_value("riders", [])
        orders = globalvar.get_value("orders", [])
        routes = [r.full_route() for r in riders if r.orders]
        return self.render_map(riders, orders, routes)

    def order_result(self, result):
        o = result["order"]
        r = result["rider"]
        lines = [
            "Order #%d created at t=%d" % (o.id, o.create_time),
            "  Restaurant: input %s -> grid %s, centre %s"
            % (o.raw_res, o.res_grid, o.res_pos),
            "  Customer:   input %s -> grid %s, centre %s"
            % (o.raw_cus, o.cus_grid, o.cus_pos),
            "  New rider added: %s" % ("yes" if result["new_rider"] else "no"),
            "  Assigned rider: #%d at (%d,%d), speed %d units/tick"
            % (r.rider_id, r.x, r.y, r.speed),
            "  Route distance: %d units, estimated time: %d ticks"
            % (result["distance"], result["estimated_ticks"]),
            "  Route: " + " -> ".join("(%d,%d)" % p for p in result["route"]),
            self.render_map([r], [x for x in r.orders], [result["route"]]),
        ]
        return "\n".join(lines)

    def status(self):
        riders = globalvar.get_value("riders", [])
        lines = [
            "Time: %d" % globalvar.get_value("time", 0),
            "Funds: %d" % globalvar.get_value("funds", 0),
            "Riders: %d" % len(riders),
        ]
        for r in riders:
            olist = ", ".join("#%d(%s)" % (o.id, o.status) for o in r.orders)
            lines.append(
                "  Rider #%d pos=(%d,%d) speed=%d state=%d(%s)%s orders=[%s]"
                % (r.rider_id, r.x, r.y, r.speed, r.state,
                   STATE_NAMES.get(r.state, "?"),
                   " special" if r.special_case else "", olist))
        return "\n".join(lines)

    def orders(self):
        orders = globalvar.get_value("orders", [])
        if not orders:
            return "No orders yet."
        lines = ["%-4s %-6s %-11s %-11s %-6s %-6s %-6s %s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Taken",
            "Rider", "Status")]
        for o in orders:
            lines.append("%-4d %-6d %-11s %-11s %-6d %-6s %-6s %s" % (
                o.id, o.create_time, "(%d,%d)" % o.res_pos,
                "(%d,%d)" % o.cus_pos, o.distance,
                "-" if o.time_taken is None else str(o.time_taken),
                "-" if o.rider_id is None else "#%d" % o.rider_id,
                o.status))
        return "\n".join(lines)

    def rider_logs(self):
        riders = globalvar.get_value("riders", [])
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider #%d (completed %d, travelled %d units)"
                         % (r.rider_id, r.completed_orders, r.total_distance))
            for e in r.log:
                oid = "" if e["order_id"] is None else " order #%d" % \
                    e["order_id"]
                lines.append("  t=%-4d %-22s at (%d,%d)%s" % (
                    e["time"], e["event"], e["x"], e["y"], oid))
        return "\n".join(lines)

    @staticmethod
    def help():
        return "\n".join([
            "Commands:",
            "  start | s [rx ry cx cy]  create an order (coords 0-800)",
            "  status | st              system snapshot",
            "  orders | o               all orders",
            "  riders | r               rider event logs",
            "  map | m                  current map",
            "  tick | t [n]             advance n ticks (default 1)",
            "  history | hi             command history",
            "  save                     save state to JSON",
            "  help | h | ?             this help",
            "  quit | exit | q          exit",
            "Every command advances the simulation by one tick.",
        ])
