"""Status display and ASCII map visualisation."""

import globalvar
from path_planner import PathPlanner, MAP_SIZE
from rider import RiderState

STEP = 50
SIZE = MAP_SIZE // STEP + 1  # 17 x 17 character grid

SYMBOLS = {
    "intersection": "+",
    "h_street": "-",
    "v_street": "|",
    "empty": ".",
    "restaurant": "R",
    "customer": "C",
    "route": "*",
    "multi_rider": "#",
}


def _cell(pos):
    col = int(pos[0] / float(STEP) + 0.5)
    row = SIZE - 1 - int(pos[1] / float(STEP) + 0.5)
    return max(0, min(SIZE - 1, row)), max(0, min(SIZE - 1, col))


class DisplayManager:
    """Builds textual views of the simulation state."""

    @staticmethod
    def _base_grid():
        grid = []
        for r in range(SIZE):
            row = []
            for c in range(SIZE):
                if r % 2 == 0 and c % 2 == 0:
                    row.append(SYMBOLS["intersection"])
                elif r % 2 == 0:
                    row.append(SYMBOLS["h_street"])
                elif c % 2 == 0:
                    row.append(SYMBOLS["v_street"])
                else:
                    row.append(SYMBOLS["empty"])
            grid.append(row)
        return grid

    @staticmethod
    def _mark_route(grid, waypoints):
        for i in range(len(waypoints) - 1):
            (x1, y1), (x2, y2) = waypoints[i], waypoints[i + 1]
            length = abs(x2 - x1) + abs(y2 - y1)
            steps = max(1, length // (STEP // 2))
            for s in range(steps + 1):
                x = x1 + (x2 - x1) * s / float(steps)
                y = y1 + (y2 - y1) * s / float(steps)
                r, c = _cell((x, y))
                if grid[r][c] in "+-|":
                    grid[r][c] = SYMBOLS["route"]

    @staticmethod
    def render_map(riders=None, orders=None, route=None):
        """Render the 8x8 grid as text.

        Riders are shown with the last digit of their id (``#`` if several
        share a spot), active restaurants as ``R``, customers as ``C`` and an
        optional route as ``*``.
        """
        if riders is None:
            riders = globalvar.get_value("riders", []) or []
        if orders is None:
            orders = [o for o in (globalvar.get_value("orders", []) or [])
                      if not o.completed]
        grid = DisplayManager._base_grid()
        if route is not None:
            DisplayManager._mark_route(grid, route.waypoints)
        for o in orders:
            r, c = _cell(o.res_pos)
            grid[r][c] = SYMBOLS["restaurant"]
            r, c = _cell(o.cus_pos)
            grid[r][c] = SYMBOLS["customer"] if grid[r][c] != "R" else "X"
        occupied = {}
        for rider in riders:
            cell = _cell(rider.position)
            occupied.setdefault(cell, []).append(rider)
        for (r, c), lst in occupied.items():
            grid[r][c] = (str(lst[0].rider_id % 10) if len(lst) == 1
                          else SYMBOLS["multi_rider"])
        lines = []
        for idx, row in enumerate(grid):
            y_val = (SIZE - 1 - idx) * STEP
            label = "%4d " % y_val if idx % 2 == 0 else "     "
            lines.append(label + " ".join(row))
        axis = "     " + " ".join(
            (str(c * STEP // 100) if c % 2 == 0 else " ") for c in range(SIZE))
        lines.append(axis + "   (x100)")
        lines.append("Legend: digit=rider  #=several riders  R=restaurant  "
                     "C=customer  X=both  *=route  +-|=streets  .=block")
        return "\n".join(lines)

    @staticmethod
    def status_text():
        """Funds, tick and per-rider status."""
        riders = globalvar.get_value("riders", []) or []
        lines = [
            "Time (tick): %s" % globalvar.get_value("tick", 0),
            "System funds: %s" % globalvar.get_value("funds", 0),
            "Rider count: %d" % len(riders),
        ]
        for r in riders:
            lines.append(
                "  Rider %d at (%d, %d) speed=%d state=%d (%s)%s orders=%d %s" % (
                    r.rider_id, r.x, r.y, r.speed, r.state,
                    RiderState.name(r.state),
                    " [special]" if r.special_case else "",
                    len(r.orders), [o.id for o in r.orders]))
        return "\n".join(lines)

    @staticmethod
    def orders_text():
        """Table of every order."""
        orders = globalvar.get_value("orders", []) or []
        if not orders:
            return "No orders yet."
        header = "%-4s %-6s %-12s %-12s %-6s %-6s %-6s %-11s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Time",
            "Rider", "Status")
        lines = [header, "-" * len(header)]
        for o in orders:
            lines.append("%-4d %-6s %-12s %-12s %-6d %-6s %-6s %-11s" % (
                o.id, o.start_time, "(%d,%d)" % o.res_pos,
                "(%d,%d)" % o.cus_pos, o.distance,
                "-" if o.time_taken is None else o.time_taken,
                "-" if o.rider_id is None else o.rider_id, o.status))
        done = [o for o in orders if o.completed]
        if done:
            avg = sum(o.time_taken for o in done) / float(len(done))
            lines.append("Completed: %d  Average time: %.1f ticks" % (len(done), avg))
        return "\n".join(lines)

    @staticmethod
    def riders_log_text():
        """Every recorded status change of every rider."""
        riders = globalvar.get_value("riders", []) or []
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append("Rider %d:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%-5s (%3s, %3s) %-22s order=%s state=%s" % (
                    e.get("time"), e.get("x"), e.get("y"), e.get("event"),
                    "-" if e.get("order_id") is None else e.get("order_id"),
                    RiderState.name(e.get("state"))))
        return "\n".join(lines)

    @staticmethod
    def order_assignment_text(order, rider, recruited):
        """Output of the ``start`` command."""
        lines = [
            "Order %d created." % order.id,
            "Restaurant grid position: (%d, %d) cell %s" % (
                order.res_pos + (PathPlanner.cell_index(order.res_pos),)),
            "Customer grid position:   (%d, %d) cell %s" % (
                order.cus_pos + (PathPlanner.cell_index(order.cus_pos),)),
            "New rider added: %s" % ("yes" if recruited else "no"),
        ]
        if rider is None:
            lines.append("No rider available; order is pending.")
            return "\n".join(lines)
        route = rider.planned_route()
        lines.append("Assigned rider: %d at (%d, %d)" % (rider.rider_id, rider.x, rider.y))
        lines.append("Speed: %d units/tick  Route length: %d  Estimated time: %d ticks"
                     % (rider.speed, route.length, route.estimated_time))
        lines.append("Route: " + " -> ".join("(%d,%d)" % p for p in route.waypoints))
        lines.append(DisplayManager.render_map(
            riders=[rider], orders=list(rider.orders), route=route))
        return "\n".join(lines)
