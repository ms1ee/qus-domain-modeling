"""Status displays and ASCII map visualization."""

from path_planner import GRID_DIM, PathPlanner, cell_index
from rider import STATE_NAMES


class DisplayManager:
    """Builds text representations of system state."""

    @staticmethod
    def render_map(riders, orders=None, route=None):
        """Render the 8x8 grid.

        'R' rider, 'S' restaurant, 'C' customer, '#' route/street, '.' empty.
        """
        grid = [["." for _ in range(GRID_DIM)] for _ in range(GRID_DIM)]
        if route:
            for x, y in PathPlanner.sample_points(route, 10):
                grid[cell_index(y)][cell_index(x)] = "#"
        for o in orders or []:
            if o.status == "completed":
                continue
            grid[cell_index(o.res_pos[1])][cell_index(o.res_pos[0])] = "S"
            grid[cell_index(o.cus_pos[1])][cell_index(o.cus_pos[0])] = "C"
        for r in riders or []:
            grid[cell_index(r.y)][cell_index(r.x)] = "R"
        lines = ["    " + " ".join(str(i) for i in range(GRID_DIM))]
        for i, row in enumerate(grid):
            lines.append("%d   %s" % (i, " ".join(row)))
        lines.append("Legend: R=Rider S=Restaurant C=Customer #=Route .=Empty")
        return "\n".join(lines)

    @staticmethod
    def status(funds, riders, time):
        """System snapshot text."""
        lines = ["Time: %d" % time, "Funds: %d" % funds, "Riders: %d" % len(riders)]
        for r in riders:
            lines.append("  Rider %s at (%d,%d) state=%s orders=%d %s" % (
                r.rider_id, r.x, r.y, STATE_NAMES.get(r.state, "?"), len(r.orders),
                [getattr(o, "id", None) for o in r.orders]))
        return "\n".join(lines)

    @staticmethod
    def orders_table(orders):
        """Details for all orders."""
        if not orders:
            return "No orders."
        lines = ["%-4s %-6s %-12s %-12s %-8s %-6s %-6s %-10s" % (
            "ID", "Start", "Restaurant", "Customer", "Dist", "Taken", "Rider", "Status")]
        for o in orders:
            lines.append("%-4s %-6s %-12s %-12s %-8s %-6s %-6s %-10s" % (
                o.id, o.created_time, "(%d,%d)" % o.res_pos, "(%d,%d)" % o.cus_pos,
                o.distance if o.distance is not None else "-",
                o.time_taken if o.time_taken is not None else "-",
                o.rider_id if o.rider_id is not None else "-", o.status))
        return "\n".join(lines)

    @staticmethod
    def rider_logs(riders):
        """Every status change of every rider."""
        if not riders:
            return "No riders."
        lines = []
        for r in riders:
            lines.append("Rider %s:" % r.rider_id)
            for e in r.log:
                lines.append("  t=%s %-22s order=%s at (%s,%s)" % (
                    e.get("time"), e["event"], e["order_id"], e.get("x"), e.get("y")))
        return "\n".join(lines)
