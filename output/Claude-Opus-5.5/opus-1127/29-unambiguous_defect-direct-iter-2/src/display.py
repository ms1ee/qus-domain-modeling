"""Status display and ASCII map visualisation."""

import globalvar
from path_planner import PathPlanner
from rider import STATE_NAMES

STEP = 50
SIZE = 800 // STEP + 1  # 17 points per axis


def _idx(v):
    return max(0, min(SIZE - 1, int(round(v / STEP))))


class DisplayManager:
    """Builds textual views of the simulation state.

    Map legend:
        +  street intersection   -  horizontal street   |  vertical street
        .  block (empty cell)    *  route               M  restaurant
        C  customer              0-9 rider (last digit of the id)
    """

    LEGEND = ("Legend: +/-/| streets  . block  * route  M restaurant  "
              "C customer  digit = rider id")

    def __init__(self, out=print):
        self.out = out

    # ------------------------------------------------------------------ #
    @staticmethod
    def _base_grid():
        grid = []
        for j in range(SIZE):
            row = []
            for i in range(SIZE):
                if i % 2 == 0 and j % 2 == 0:
                    row.append("+")
                elif i % 2 == 0:
                    row.append("|")
                elif j % 2 == 0:
                    row.append("-")
                else:
                    row.append(".")
            grid.append(row)
        return grid

    @staticmethod
    def _draw_route(grid, route):
        for a, b in zip(route, route[1:]):
            ai, aj = _idx(a[0]), _idx(a[1])
            bi, bj = _idx(b[0]), _idx(b[1])
            if aj == bj:
                step = 1 if bi >= ai else -1
                for i in range(ai, bi + step, step):
                    grid[aj][i] = "*"
            elif ai == bi:
                step = 1 if bj >= aj else -1
                for j in range(aj, bj + step, step):
                    grid[j][ai] = "*"
            else:
                grid[aj][ai] = "*"
                grid[bj][bi] = "*"

    def render_map(self, riders=None, orders=None, route=None):
        """Return the ASCII map as a string."""
        riders = riders if riders is not None else (
            globalvar.get_value("riders") or [])
        if orders is None:
            orders = [o for o in (globalvar.get_value("orders") or [])
                      if o.status != "completed"]
        grid = self._base_grid()
        if route:
            self._draw_route(grid, route)
        for o in orders:
            grid[_idx(o.res_pos[1])][_idx(o.res_pos[0])] = "M"
            grid[_idx(o.cus_pos[1])][_idx(o.cus_pos[0])] = "C"
        for r in riders:
            grid[_idx(r.y)][_idx(r.x)] = str(r.rider_id % 10)
        lines = ["     " + " ".join(f"{i * STEP // 100}" if i % 2 == 0
                                    else " " for i in range(SIZE)),
                 ]
        for j, row in enumerate(grid):
            label = f"{j * STEP:>3}" if j % 2 == 0 else "   "
            lines.append(f"{label}  " + " ".join(row))
        lines.append("(x axis in hundreds, y axis in units; y grows down)")
        lines.append(self.LEGEND)
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    def show_map(self, route=None):
        """Print the map."""
        self.out(self.render_map(route=route))

    def show_status(self):
        """Print funds and the state of every rider."""
        riders = globalvar.get_value("riders") or []
        self.out(f"Time: {globalvar.get_value('time', 0)}  "
                 f"Funds: {globalvar.get_value('funds', 0)}  "
                 f"Riders: {len(riders)}")
        if not riders:
            self.out("  (no riders yet)")
        for r in riders:
            ids = [o.id for o in r.orders]
            flag = " [special]" if r.special_case else ""
            self.out(f"  Rider {r.rider_id}: pos=({r.x},{r.y}) "
                     f"speed={r.speed} state={r.state}"
                     f"({STATE_NAMES.get(r.state, '?')}) "
                     f"orders={len(r.orders)} {ids}{flag}")

    def show_orders(self):
        """Print every order with its details."""
        orders = globalvar.get_value("orders") or []
        if not orders:
            self.out("No orders yet.")
            return
        self.out(f"{'ID':>3} {'Start':>5} {'Restaurant':>11} "
                 f"{'Customer':>11} {'Dist':>5} {'Taken':>5} "
                 f"{'Rider':>5}  Status")
        for o in orders:
            taken = "-" if o.time_taken is None else str(o.time_taken)
            rid = "-" if o.rider_id is None else str(o.rider_id)
            self.out(f"{o.id:>3} {o.start_time:>5} "
                     f"{str(o.res_pos):>11} {str(o.cus_pos):>11} "
                     f"{o.route_distance:>5} {taken:>5} {rid:>5}  "
                     f"{o.status}")

    def show_rider_logs(self):
        """Print every rider status change."""
        riders = globalvar.get_value("riders") or []
        if not riders:
            self.out("No riders yet.")
            return
        for r in riders:
            self.out(f"Rider {r.rider_id}:")
            for e in r.log:
                oid = "-" if e.get("order_id") is None else e["order_id"]
                self.out(f"  t={e.get('time', 0):>4} {e['event']:<22} "
                         f"order={oid:<4} pos=({e.get('x')},{e.get('y')})")

    def show_assignment(self, result):
        """Print the outcome of a ``start`` command."""
        order = result["order"]
        rider = result["rider"]
        rc = PathPlanner.to_cell(order.res_pos)
        cc = PathPlanner.to_cell(order.cus_pos)
        self.out(f"Order #{order.id} created.")
        self.out(f"  Restaurant: {order.res_pos} (cell {rc})")
        self.out(f"  Customer:   {order.cus_pos} (cell {cc})")
        self.out(f"  New rider added: {'yes' if result['added'] else 'no'}")
        self.out(f"  Assigned rider: {rider.rider_id} "
                 f"(speed {rider.speed} units/tick)")
        self.out(f"  Route distance: {result['distance']}  "
                 f"Estimated time: {result['eta']} ticks")
        self.out(self.render_map(route=result["route"]))
