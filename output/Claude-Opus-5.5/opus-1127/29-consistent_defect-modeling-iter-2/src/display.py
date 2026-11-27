"""Status display and ASCII map visualisation."""

from path_planner import MAP_SIZE
from rider import STATE_NAMES, RiderState


class DisplayManager:
    """Renders status tables and a 16x16 ASCII map (50 units per char)."""

    def __init__(self, map_display_size=16, map_size=MAP_SIZE):
        self.map_display_size = map_display_size
        self.map_size = map_size
        self.unit = map_size // map_display_size

    def _idx(self, v):
        return max(0, min(self.map_display_size - 1, int(v) // self.unit))

    def render_map(self, riders, orders, route=None):
        """Render the map.

        Symbols: R rider, S restaurant, C customer, * route,
        # street, . empty space.
        """
        n = self.map_display_size
        grid = [['#' if (r % 2 == 0 or c % 2 == 0) else '.' for c in range(n)]
                for r in range(n)]
        if route and len(route) > 1:
            for a, b in zip(route, route[1:]):
                length = abs(b[0] - a[0]) + abs(b[1] - a[1])
                steps = max(1, length // (self.unit // 2))
                for i in range(steps + 1):
                    x = a[0] + (b[0] - a[0]) * i // steps
                    y = a[1] + (b[1] - a[1]) * i // steps
                    grid[self._idx(y)][self._idx(x)] = '*'
        for o in orders:
            grid[self._idx(o.cus_pos[1])][self._idx(o.cus_pos[0])] = 'C'
        for o in orders:
            grid[self._idx(o.res_pos[1])][self._idx(o.res_pos[0])] = 'S'
        for r in riders:
            grid[self._idx(r.y)][self._idx(r.x)] = 'R'
        lines = ["     " + "".join(str((c * self.unit) // 100 % 10) if c % 2 == 0 else ' '
                                   for c in range(n))]
        for r in range(n):
            lines.append(f"{r * self.unit:4d} " + "".join(grid[r]))
        lines.append("Legend: R=rider S=restaurant C=customer *=route #=street .=empty"
                     " (x labels in hundreds)")
        return "\n".join(lines)

    def format_status(self, funds, tick, riders):
        lines = [f"Tick: {tick}", f"System funds: {funds}",
                 f"Riders: {len(riders)}"]
        for r in riders:
            name = STATE_NAMES.get(RiderState(r.state), str(r.state))
            ids = [o.id for o in r.orders]
            lines.append(
                f"  Rider #{r.rider_id}: pos=({r.x},{r.y}) state={int(r.state)}"
                f"({name}) active={r.active_order_count} total={len(r.orders)}"
                f" orders={ids}")
        return "\n".join(lines)

    def format_orders(self, orders):
        if not orders:
            return "No orders yet."
        header = (f"{'ID':>3} {'Start':>5} {'Restaurant':>11} {'Customer':>11} "
                  f"{'Dist':>5} {'Time':>5} {'Rider':>5} Status")
        lines = [header, "-" * len(header)]
        for o in orders:
            res = f"({o.res_pos[0]},{o.res_pos[1]})"
            cus = f"({o.cus_pos[0]},{o.cus_pos[1]})"
            t = "-" if o.time_taken is None else str(o.time_taken)
            rid = "-" if o.rider_id is None else str(o.rider_id)
            lines.append(f"{o.id:>3} {o.start_time:>5} {res:>11} {cus:>11} "
                         f"{o.distance:>5} {t:>5} {rid:>5} {o.status}")
        return "\n".join(lines)

    def format_rider_logs(self, riders):
        if not riders:
            return "No riders yet."
        lines = []
        for r in riders:
            lines.append(f"Rider #{r.rider_id}:")
            for e in r.log:
                oid = "-" if e.get("order_id") is None else e.get("order_id")
                lines.append(f"  t={e.get('time', 0):>4} {e['event']:<22} "
                             f"pos=({e.get('x')},{e.get('y')}) order={oid}")
        return "\n".join(lines)
