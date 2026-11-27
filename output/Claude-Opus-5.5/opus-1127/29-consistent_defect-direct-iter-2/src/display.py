"""Status display and ASCII map visualisation."""

import globalvar
from rider import STATE_NAMES

SIZE = 16
UNIT = 50


def _idx(v):
    return max(0, min(SIZE - 1, int(v) // UNIT))


class DisplayManager:
    """Builds textual views of the system."""

    def base_map(self):
        grid = []
        for r in range(SIZE):
            row = []
            for c in range(SIZE):
                row.append("#" if (r % 2 == 0 or c % 2 == 0) else ".")
            grid.append(row)
        return grid

    def draw_route(self, grid, points):
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            c1, r1, c2, r2 = _idx(x1), _idx(y1), _idx(x2), _idx(y2)
            for c in range(min(c1, c2), max(c1, c2) + 1):
                grid[r1][c] = "*"
            for r in range(min(r1, r2), max(r1, r2) + 1):
                grid[r][c2] = "*"

    def render(self, route=None, orders=None):
        """Render the map with riders, restaurants, customers and route."""
        grid = self.base_map()
        if route:
            self.draw_route(grid, route)
        orders = orders if orders is not None else [
            o for o in globalvar.get_value("orders") or []
            if o.status != "completed"]
        for o in orders:
            grid[_idx(o.res_pos[1])][_idx(o.res_pos[0])] = "S"
            grid[_idx(o.cus_pos[1])][_idx(o.cus_pos[0])] = "C"
        for r in globalvar.get_value("riders") or []:
            grid[_idx(r.y)][_idx(r.x)] = "R"
        return "\n".join(" ".join(row) for row in grid)

    def status(self):
        lines = ["Time: %s" % globalvar.get_value("time"),
                 "Funds: %s" % globalvar.get_value("money")]
        riders = globalvar.get_value("riders") or []
        lines.append("Riders: %d" % len(riders))
        for r in riders:
            lines.append("  Rider %d at (%d, %d) state=%s orders=%s active=%d" % (
                r.rider_id, r.x, r.y, STATE_NAMES.get(r.state, r.state),
                [o.id for o in r.orders], len(r.active_orders())))
        lines.append(self.render())
        return "\n".join(lines)

    def orders(self):
        lines = []
        for o in globalvar.get_value("orders") or []:
            lines.append(
                "Order %d: start=%s restaurant=%s customer=%s distance=%d "
                "time_taken=%s rider=%s status=%s" % (
                    o.id, o.create_time, o.res_pos, o.cus_pos, o.distance,
                    o.time_taken(), o.rider_id, o.status))
        return "\n".join(lines) or "No orders."

    def riders(self):
        lines = []
        for r in globalvar.get_value("riders") or []:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%s %s order=%s at (%s, %s)" % (
                    e.get("time"), e["event"], e["order_id"], e.get("x"), e.get("y")))
        return "\n".join(lines) or "No riders."
