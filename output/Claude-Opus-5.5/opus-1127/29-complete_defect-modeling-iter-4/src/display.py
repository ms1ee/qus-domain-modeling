"""Status display and ASCII map visualisation."""

import globalvar
from path_planner import GRID_DIMENSION, to_grid_index
from rider import RiderState

FINE_SIZE = 17  # 0..800 in steps of 50


def _fine_index(value):
    idx = int(round(value / 50.0))
    return max(0, min(FINE_SIZE - 1, idx))


class DisplayManager:
    """Renders status information and maps as text."""

    # -------------------------------------------------------------- maps
    @staticmethod
    def render_grid():
        """Render the 8x8 cell map: R rider, S restaurant, C customer,
        '#' cells on active routes, '.' empty."""
        grid = [["." for _ in range(GRID_DIMENSION)]
                for _ in range(GRID_DIMENSION)]
        riders = globalvar.get_value("riders", []) or []
        for rider in riders:
            prev = (rider.x, rider.y)
            for point in rider.path:
                for cx, cy in DisplayManager._cells_on_segment(prev, point):
                    grid[cy][cx] = "#"
                prev = point
        for rider in riders:
            for order in rider.pending_orders():
                cx, cy = order.customer_cell
                grid[cy][cx] = "C"
        for rider in riders:
            for order in rider.pending_orders():
                rx, ry = order.restaurant_cell
                grid[ry][rx] = "S"
        for rider in riders:
            grid[to_grid_index(rider.y)][to_grid_index(rider.x)] = "R"
        lines = ["    " + " ".join(str(i) for i in range(GRID_DIMENSION))]
        for y in range(GRID_DIMENSION):
            lines.append("{:>3} ".format(y) + " ".join(grid[y]))
        lines.append("Legend: R=Rider S=Restaurant C=Customer #=Route .=Empty")
        return "\n".join(lines)

    @staticmethod
    def _cells_on_segment(a, b):
        cells = []
        x0, y0 = to_grid_index(a[0]), to_grid_index(a[1])
        x1, y1 = to_grid_index(b[0]), to_grid_index(b[1])
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                cells.append((x, y))
        return cells

    @staticmethod
    def render_route(route, restaurant=None, customer=None):
        """Render a route as connected line segments on a street map.

        Grid lines (streets) are at multiples of 100, '+' marks
        intersections, '.' marks cell centres, '#' the route.
        """
        grid = []
        for r in range(FINE_SIZE):
            row = []
            for c in range(FINE_SIZE):
                if r % 2 == 0 and c % 2 == 0:
                    row.append("+")
                elif r % 2 == 1 and c % 2 == 1:
                    row.append(".")
                else:
                    row.append(" ")
            grid.append(row)
        points = route.waypoints if route else []
        for a, b in zip(points, points[1:]):
            ax, ay = _fine_index(a[0]), _fine_index(a[1])
            bx, by = _fine_index(b[0]), _fine_index(b[1])
            for x in range(min(ax, bx), max(ax, bx) + 1):
                grid[ay][x] = "#"
            for y in range(min(ay, by), max(ay, by) + 1):
                grid[y][bx] = "#"
        if customer:
            grid[_fine_index(customer[1])][_fine_index(customer[0])] = "C"
        if restaurant:
            grid[_fine_index(restaurant[1])][_fine_index(restaurant[0])] = "S"
        if points:
            grid[_fine_index(points[0][1])][_fine_index(points[0][0])] = "R"
        header = "      " + " ".join(
            str(c * 50 // 100) if c % 2 == 0 else " " for c in range(FINE_SIZE))
        lines = [header + "   (x100)"]
        for r in range(FINE_SIZE):
            lines.append("{:>5} ".format(r * 50) + " ".join(grid[r]))
        return "\n".join(lines)

    # ------------------------------------------------------------ reports
    @staticmethod
    def format_start_result(result):
        order = result["order"]
        rider = result["rider"]
        route = result["route"]
        lines = [
            "Order #{} created at tick {}".format(order.id, order.start_time),
            "  Restaurant {} -> grid cell {} centre {}".format(
                order.raw_restaurant, order.restaurant_cell, order.res_pos),
            "  Customer   {} -> grid cell {} centre {}".format(
                order.raw_customer, order.customer_cell, order.cus_pos),
        ]
        if result["new_riders"]:
            lines.append("  New rider added: yes (IDs: {})".format(
                ", ".join(str(r.rider_id) for r in result["new_riders"])))
        else:
            lines.append("  New rider added: no")
        if rider is None:
            lines.append("  No rider available - order queued for dispatch.")
            return "\n".join(lines)
        lines.append("  Assigned rider: {} (state: {}, speed: {} units/tick)".format(
            rider.rider_id, RiderState.name(rider.state), rider.speed))
        lines.append("  Route: " + " -> ".join(
            "({},{})".format(x, y) for x, y in route.waypoints))
        lines.append("  Route length: {} units, estimated time: {} ticks{}".format(
            route.length, route.estimated_time,
            " (special case: straight vertical leg)" if route.special_case else ""))
        lines.append(DisplayManager.render_route(route, order.res_pos,
                                                 order.cus_pos))
        return "\n".join(lines)

    @staticmethod
    def format_status():
        riders = globalvar.get_value("riders", []) or []
        pending = globalvar.get_value("pending_orders", []) or []
        lines = [
            "Tick: {}".format(globalvar.get_value("tick", 0)),
            "Funds: {}".format(globalvar.get_value("funds", 0)),
            "Riders: {}".format(len(riders)),
        ]
        for rider in riders:
            orders = ", ".join("#{}({})".format(o.id, o.status)
                               for o in rider.orders) or "none"
            lines.append("  Rider {:>2} at ({:>3},{:>3}) speed {:>3} {:<11} "
                         "special={} orders: {}".format(
                             rider.rider_id, rider.x, rider.y, rider.speed,
                             RiderState.name(rider.state),
                             rider.special_case, orders))
        if pending:
            lines.append("Queued orders: " + ", ".join(
                "#{}".format(o.id) for o in pending))
        lines.append(DisplayManager.render_grid())
        return "\n".join(lines)

    @staticmethod
    def format_orders():
        orders = globalvar.get_value("orders", []) or []
        if not orders:
            return "No orders yet."
        lines = ["{:>4} {:>6} {:>12} {:>12} {:>8} {:>6} {:>6} {:<10}".format(
            "ID", "Start", "Restaurant", "Customer", "Distance", "Time",
            "Rider", "Status")]
        for o in orders:
            lines.append("{:>4} {:>6} {:>12} {:>12} {:>8} {:>6} {:>6} {:<10}".format(
                o.id, o.start_time, "({},{})".format(*o.res_pos),
                "({},{})".format(*o.cus_pos), o.distance,
                "-" if o.time_taken is None else o.time_taken,
                "-" if o.rider_id is None else o.rider_id, o.status))
        return "\n".join(lines)

    @staticmethod
    def format_rider_logs():
        riders = globalvar.get_value("riders", []) or []
        if not riders:
            return "No riders yet."
        lines = []
        for rider in riders:
            lines.append("Rider {}:".format(rider.rider_id))
            for entry in rider.log:
                lines.append("  t={:>4} ({:>3},{:>3}) {:<22} order: {}".format(
                    entry["time"], entry["x"], entry["y"], entry["event"],
                    "-" if entry["order_id"] is None else entry["order_id"]))
        return "\n".join(lines)
