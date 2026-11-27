"""Status display and ASCII map visualisation."""

from path_planner import MAP_SIZE
from rider import STATE_NAMES

MAP_CELLS = 16
CHAR_CELL = MAP_SIZE // MAP_CELLS  # 50 units per character cell


def _cell(value):
    return max(0, min(MAP_CELLS - 1, int(value) // CHAR_CELL))


class DisplayManager:
    """Builds textual views of the system state."""

    @staticmethod
    def render_map(riders=None, orders=None, route=None):
        """Render a 16x16 ASCII map.

        '#' street, '.' block, '*' route, 'S' restaurant, 'C' customer,
        'R' rider.
        """
        grid = [["#" if (r % 2 == 0 or c % 2 == 0) else "."
                 for c in range(MAP_CELLS)] for r in range(MAP_CELLS)]
        if route and len(route) > 1:
            for (x1, y1), (x2, y2) in zip(route, route[1:]):
                c1, r1, c2, r2 = _cell(x1), _cell(y1), _cell(x2), _cell(y2)
                for c in range(min(c1, c2), max(c1, c2) + 1):
                    grid[r1][c] = "*"
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    grid[r][c2] = "*"
        for order in orders or []:
            if order.status == "completed":
                continue
            grid[_cell(order.res_pos[1])][_cell(order.res_pos[0])] = "S"
            grid[_cell(order.cus_pos[1])][_cell(order.cus_pos[0])] = "C"
        for rider in riders or []:
            grid[_cell(rider.y)][_cell(rider.x)] = "R"
        header = "   " + "".join("{:X}".format(i) for i in range(MAP_CELLS))
        lines = [header]
        for idx, row in enumerate(grid):
            lines.append("{:2X} ".format(idx) + "".join(row))
        lines.append("Legend: R=rider S=restaurant C=customer "
                     "#=street .=block *=route (1 char = 50 units)")
        return "\n".join(lines)

    @staticmethod
    def format_route(rider, orders=None):
        """Route map plus speed and estimated time for a rider."""
        route = rider.planned_route()
        lines = ["Rider {} route: {}".format(
            rider.rider_id, " -> ".join("({},{})".format(x, y) for x, y in route))]
        lines.append("Speed: {} units/tick, estimated time: {} ticks".format(
            rider.speed, rider.estimated_ticks()))
        active = [o for o in rider.orders if o.status != "completed"]
        lines.append(DisplayManager.render_map([rider], orders or active, route))
        return "\n".join(lines)

    @staticmethod
    def format_status(funds, riders, current_time=0):
        """System funds and rider overview."""
        lines = ["Time: {}  Funds: {}  Riders: {}".format(
            current_time, funds, len(riders))]
        for r in riders:
            order_ids = [o.id for o in r.orders]
            lines.append(
                "  Rider {:>3} at ({:>3},{:>3}) state={:<11} active={} "
                "orders={}".format(r.rider_id, r.x, r.y,
                                   STATE_NAMES.get(r.state, r.state),
                                   r.active_order_count(), order_ids))
        if not riders:
            lines.append("  (no riders)")
        return "\n".join(lines)

    @staticmethod
    def format_orders(orders):
        """Detailed order table."""
        if not orders:
            return "No orders."
        lines = ["{:>4} {:>6} {:>11} {:>11} {:>6} {:>6} {:>6} {:<11}".format(
            "ID", "Start", "Restaurant", "Customer", "Dist", "Time",
            "Rider", "Status")]
        for o in orders:
            taken = o.time_taken
            lines.append("{:>4} {:>6} {:>11} {:>11} {:>6} {:>6} {:>6} {:<11}".format(
                o.id, o.created_time,
                "({},{})".format(*o.res_pos), "({},{})".format(*o.cus_pos),
                o.distance, "-" if taken is None else taken,
                "-" if o.rider_id is None else o.rider_id, o.status))
        return "\n".join(lines)

    @staticmethod
    def format_rider_logs(riders):
        """Every recorded status change for every rider."""
        if not riders:
            return "No riders."
        lines = []
        for r in riders:
            lines.append("Rider {}:".format(r.rider_id))
            for e in r.log:
                lines.append("  t={:<5} ({:>3},{:>3}) {:<22} order={}".format(
                    e.get("time", "-"), e.get("x", "-"), e.get("y", "-"),
                    e["event"], "-" if e["order_id"] is None else e["order_id"]))
        return "\n".join(lines)
