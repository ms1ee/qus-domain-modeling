"""Grid based path planning.

Coordinate system: an 800x800 map split into 8x8 cells of 100x100 units.
Streets run along the grid lines (x or y a multiple of 100). Restaurants and
customers sit at cell centres (e.g. (150, 250)). Riders always move on the
streets, using horizontal and vertical segments with right-angle turns.
A restaurant/customer is "reached" when the rider stands on the street
point next to the cell centre (the midpoint of one of the cell edges).
"""

import heapq

GRID_SIZE = 100
MAP_SIZE = 800


class PathPlanner:
    """Shortest path computation on the street network."""

    def __init__(self, grid_size=GRID_SIZE, map_size=MAP_SIZE):
        """Create a planner for a ``map_size`` square map of ``grid_size`` cells."""
        self.grid_size = grid_size
        self.map_size = map_size

    # ------------------------------------------------------------------ basics
    def clamp(self, value):
        """Clamp a coordinate into ``[0, map_size]`` as an integer."""
        return max(0, min(self.map_size, int(round(value))))

    @staticmethod
    def manhattan(a, b):
        """Manhattan distance between two points."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def is_on_road(self, x, y):
        """Return True if (x, y) lies on a street."""
        g = self.grid_size
        return (0 <= x <= self.map_size and 0 <= y <= self.map_size
                and (x % g == 0 or y % g == 0))

    def is_intersection(self, p):
        """Return True if ``p`` is a street intersection."""
        return p[0] % self.grid_size == 0 and p[1] % self.grid_size == 0

    def snap_to_road(self, x, y):
        """Return the nearest street point to (x, y)."""
        x, y = self.clamp(x), self.clamp(y)
        if self.is_on_road(x, y):
            return (x, y)
        g = self.grid_size
        rx = int(round(x / g)) * g
        ry = int(round(y / g)) * g
        if abs(rx - x) <= abs(ry - y):
            return (rx, y)
        return (x, ry)

    def to_grid_center(self, x, y):
        """Convert raw input coordinates to the centre of the containing cell.

        ``center = (coord // 100) * 100 + 50``; boundary values (800) map to
        the last cell, negative values to the first.
        """
        g = self.grid_size
        cells = self.map_size // g
        gx = min(self.clamp(x) // g, cells - 1)
        gy = min(self.clamp(y) // g, cells - 1)
        return (gx * g + g // 2, gy * g + g // 2)

    def grid_index(self, pos):
        """Return the (column, row) cell index containing ``pos``."""
        cells = self.map_size // self.grid_size
        return (min(int(pos[0]) // self.grid_size, cells - 1),
                min(int(pos[1]) // self.grid_size, cells - 1))

    def access_points(self, center):
        """Street points adjacent to a cell centre (edge midpoints)."""
        h = self.grid_size // 2
        cx, cy = center
        points = [(cx, cy - h), (cx, cy + h), (cx - h, cy), (cx + h, cy)]
        return [p for p in points if self.is_on_road(*p)]

    def is_special_case(self, start, center):
        """True if the rider is directly above/below the target cell centre.

        In this case the rider cannot drive straight towards it (it would cut
        through blocks) and must detour to a neighbouring vertical street.
        """
        return start[0] == center[0] and start[1] != center[1]

    # --------------------------------------------------------------- dijkstra
    def _segment_endpoints(self, p):
        """Intersections bounding the street segment containing ``p``."""
        g = self.grid_size
        x, y = p
        if y % g == 0:
            base = (x // g) * g
            return ((base, y), (base + g, y))
        base = (y // g) * g
        return ((x, base), (x, base + g))

    def _neighbors(self, node, extra):
        """Adjacent nodes of ``node`` with edge lengths."""
        result = []
        if self.is_intersection(node):
            g = self.grid_size
            x, y = node
            for dx, dy in ((g, 0), (-g, 0), (0, g), (0, -g)):
                nx, ny = x + dx, y + dy
                if 0 <= nx <= self.map_size and 0 <= ny <= self.map_size:
                    result.append(((nx, ny), g))
        result.extend(extra.get(node, []))
        return result

    @staticmethod
    def _compress(points):
        """Remove collinear intermediate points from a polyline."""
        if len(points) < 3:
            return list(points)
        out = [points[0]]
        for i in range(1, len(points) - 1):
            a, b, c = out[-1], points[i], points[i + 1]
            if (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1]):
                continue
            out.append(b)
        out.append(points[-1])
        return out

    def shortest_path(self, start, goal):
        """Shortest street path from ``start`` to ``goal``.

        :return: ``(length, waypoints)`` where waypoints exclude the start and
                 end with the goal. ``(None, [])`` if unreachable.
        """
        start = self.snap_to_road(*start)
        goal = self.snap_to_road(*goal)
        if start == goal:
            return 0, []
        extra = {}

        def add(a, b):
            d = self.manhattan(a, b)
            extra.setdefault(a, []).append((b, d))
            extra.setdefault(b, []).append((a, d))

        for p in (start, goal):
            if not self.is_intersection(p):
                for e in self._segment_endpoints(p):
                    add(p, e)
        if (not self.is_intersection(start) and not self.is_intersection(goal)
                and self._segment_endpoints(start)
                == self._segment_endpoints(goal)):
            add(start, goal)

        inf = float("inf")
        dist = {start: 0}
        prev = {}
        heap = [(0, 0, start)]
        counter = 1
        while heap:
            d, _, node = heapq.heappop(heap)
            if node == goal:
                break
            if d > dist.get(node, inf):
                continue
            for nb, w in self._neighbors(node, extra):
                nd = d + w
                if nd < dist.get(nb, inf):
                    dist[nb] = nd
                    prev[nb] = node
                    heapq.heappush(heap, (nd, counter, nb))
                    counter += 1
        if goal not in dist:
            return None, []
        nodes = [goal]
        while nodes[-1] != start:
            nodes.append(prev[nodes[-1]])
        nodes.reverse()
        nodes = self._compress(nodes)
        return dist[goal], nodes[1:]

    def best_access(self, start, center):
        """Choose the access point of ``center`` with the shortest path.

        :return: ``(access_point, waypoints, length)``
        """
        best = None
        for ap in self.access_points(center):
            length, path = self.shortest_path(start, ap)
            if length is None:
                continue
            if best is None or length < best[2]:
                best = (ap, path, length)
        if best is None:
            ap = self.snap_to_road(*center)
            return ap, [ap], self.manhattan(start, ap)
        return best

    def plan_order_route(self, start, res_center, cus_center):
        """Plan the continuous route rider -> restaurant -> customer.

        :return: dict with ``waypoints`` (including start), ``pickup``,
                 ``dropoff``, ``pickup_length``, ``delivery_length``, ``total``.
        """
        start = self.snap_to_road(*start)
        ap1, p1, l1 = self.best_access(start, res_center)
        ap2, p2, l2 = self.best_access(ap1, cus_center)
        return {
            "waypoints": [start] + list(p1) + list(p2),
            "pickup": ap1,
            "dropoff": ap2,
            "pickup_length": l1,
            "delivery_length": l2,
            "total": l1 + l2,
        }


planner = PathPlanner()
