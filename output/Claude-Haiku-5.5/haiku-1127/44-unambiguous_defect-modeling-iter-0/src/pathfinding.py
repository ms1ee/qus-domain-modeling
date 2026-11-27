"""
Path calculation for the subway network.

Contains:
  * ``MinPQ``: an indexed binary min-heap supporting decrease-key, which gives
    Dijkstra's algorithm its O((V+E) log V) running time.
  * ``PathfindingConfig``: query mode, transfer limit and line preferences.
  * ``ShortestPath``: Dijkstra's algorithm over a state space of
    (station, arriving line, transfers so far), so that transfers at
    multi-line interchange stations are handled correctly.
"""

MODE_SHORTEST_DISTANCE = "shortest_distance"
MODE_LEAST_TRANSFER = "least_transfer"
MODE_COMPREHENSIVE = "comprehensive"
VALID_MODES = (MODE_SHORTEST_DISTANCE, MODE_LEAST_TRANSFER, MODE_COMPREHENSIVE)

# Equivalent distance (meters) penalty per transfer used by the comprehensive mode.
TRANSFER_PENALTY_METERS = 1000.0
# Equivalent distance (meters) penalty for riding a line outside the preferences.
PREFERENCE_PENALTY_METERS = 300.0


class MinPQ:
    """
    Indexed binary min-heap priority queue.

    Items are non-negative integers. Each item may be present at most once;
    its key can be lowered with ``decrease_key``.

    Attributes:
        size (int): Number of items currently in the queue.
        capacity (int): Number of item slots currently allocated.
    """

    def __init__(self, capacity=16):
        size = max(1, int(capacity))
        self._keys = [None] * size      # item -> key
        self._qp = [-1] * size          # item -> position in heap, -1 if absent
        self._heap = []                 # heap-ordered list of items

    @property
    def size(self):
        return len(self._heap)

    @property
    def capacity(self):
        return len(self._qp)

    def is_empty(self):
        """Return True if the queue has no items."""
        return not self._heap

    def contains(self, item):
        """Return True if the item is currently in the queue."""
        return 0 <= item < len(self._qp) and self._qp[item] != -1

    def _ensure_slot(self, item):
        if item >= len(self._qp):
            grow = item + 1 - len(self._qp)
            self._qp.extend([-1] * grow)
            self._keys.extend([None] * grow)

    def insert(self, item, key):
        """Insert an item with the given key."""
        if item < 0:
            raise ValueError("Items must be non-negative integers")
        self._ensure_slot(item)
        if self.contains(item):
            raise ValueError(f"Item {item} is already in the queue")
        self._keys[item] = key
        self._heap.append(item)
        self._qp[item] = len(self._heap) - 1
        self._swim(len(self._heap) - 1)

    def min_item(self):
        """Return the item with the smallest key without removing it."""
        if not self._heap:
            raise IndexError("Priority queue is empty")
        return self._heap[0]

    def min_key(self):
        """Return the smallest key in the queue."""
        return self._keys[self.min_item()]

    def decrease_key(self, item, key):
        """Lower the key of an item already in the queue."""
        if not self.contains(item):
            raise KeyError(f"Item {item} is not in the queue")
        if key > self._keys[item]:
            raise ValueError("New key must not be greater than the current key")
        self._keys[item] = key
        self._swim(self._qp[item])

    def del_min(self):
        """Remove and return the item with the smallest key."""
        if not self._heap:
            raise IndexError("Priority queue is empty")
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._qp[last] = 0
            self._sink(0)
        self._qp[top] = -1
        self._keys[top] = None
        return top

    # Heap helpers -------------------------------------------------------
    def _greater(self, i, j):
        return self._keys[self._heap[i]] > self._keys[self._heap[j]]

    def _swap(self, i, j):
        a = self._heap[i]
        b = self._heap[j]
        self._heap[i] = b
        self._heap[j] = a
        self._qp[b] = i
        self._qp[a] = j

    def _swim(self, k):
        while k > 0:
            parent = (k - 1) // 2
            if self._greater(parent, k):
                self._swap(parent, k)
                k = parent
            else:
                break

    def _sink(self, k):
        n = len(self._heap)
        while True:
            child = 2 * k + 1
            if child >= n:
                break
            if child + 1 < n and self._greater(child, child + 1):
                child += 1
            if not self._greater(k, child):
                break
            self._swap(k, child)
            k = child


class PathfindingConfig:
    """
    Configuration of a path query.

    Attributes:
        mode (str): One of VALID_MODES.
        max_transfers (int | None): Maximum allowed transfers, None means unlimited.
        preferred_lines (list[str]): Lines the passenger prefers to ride.
    """

    def __init__(self, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, preferred_lines=None):
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode '{mode}', expected one of {', '.join(VALID_MODES)}")
        if max_transfers is not None:
            if isinstance(max_transfers, bool) or not isinstance(max_transfers, int):
                raise ValueError("max_transfers must be an integer")
            if max_transfers < 0:
                raise ValueError("max_transfers must not be negative")
        if preferred_lines is None:
            preferred_lines = []
        elif isinstance(preferred_lines, str):
            preferred_lines = preferred_lines.split(",")
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines = [str(line).strip() for line in preferred_lines if str(line).strip()]


def count_transfers(edges):
    """Count line changes along a sequence of consecutive edges."""
    return sum(1 for prev, nxt in zip(edges, edges[1:]) if prev.line != nxt.line)


class ShortestPath:
    """
    Dijkstra-based optimal path computation from one source station.

    The search runs over states (station, arriving line, transfers so far).
    The cost ordering depends on the mode:
      * shortest_distance: total distance (plus preference penalties)
      * least_transfer:    (transfers, distance) lexicographically
      * comprehensive:     distance + TRANSFER_PENALTY_METERS * transfers

    Attributes:
        algorithm (str): Name of the algorithm ("Dijkstra").
        dist_to (dict): Station number -> travelled distance in meters on the
            best path found for that station.
    """

    algorithm = "Dijkstra"

    def __init__(self, graph, source, config=None):
        if not graph.has_node(source):
            raise ValueError(f"Source station {source} is not in the graph")
        self.graph = graph
        self.source = source
        self.config = config or PathfindingConfig()
        self.dist_to = {}
        self._state_node = []
        self._state_line = []
        self._state_trans = []
        self._state_dist = []
        self._state_pen = []
        self._state_key = []
        self._state_prev = []
        self._state_edge = []
        self._state_index = {}
        self._best_state = {}
        self._run()

    def _key(self, distance, transfers, penalty):
        """Compute the priority key of a state according to the query mode."""
        mode = self.config.mode
        if mode == MODE_LEAST_TRANSFER:
            return (transfers, distance + penalty)
        if mode == MODE_COMPREHENSIVE:
            return distance + penalty + TRANSFER_PENALTY_METERS * transfers
        return distance + penalty

    def _add_state(self, node, line, transfers, distance, penalty, key, prev, edge):
        sid = len(self._state_node)
        self._state_node.append(node)
        self._state_line.append(line)
        self._state_trans.append(transfers)
        self._state_dist.append(distance)
        self._state_pen.append(penalty)
        self._state_key.append(key)
        self._state_prev.append(prev)
        self._state_edge.append(edge)
        self._state_index[(node, line, transfers)] = sid
        return sid

    def _run(self):
        """Execute Dijkstra's algorithm over the state space."""
        cfg = self.config
        preferred = set(cfg.preferred_lines)
        max_transfers = cfg.max_transfers

        pq = MinPQ(capacity=max(16, 2 * self.graph.edge_count + 1))
        start_key = self._key(0.0, 0, 0.0)
        start = self._add_state(self.source, None, 0, 0.0, 0.0, start_key, -1, None)
        pq.insert(start, start_key)

        settled = set()
        while not pq.is_empty():
            s = pq.del_min()
            settled.add(s)
            node = self._state_node[s]
            line_in = self._state_line[s]
            trans_s = self._state_trans[s]
            dist_s = self._state_dist[s]
            pen_s = self._state_pen[s]

            for edge in self.graph.adjacent_edges(node):
                nxt = edge.other(node)
                line = edge.line
                new_trans = trans_s + (1 if line_in is not None and line != line_in else 0)
                if max_transfers is not None and new_trans > max_transfers:
                    continue
                new_dist = dist_s + edge.distance
                new_pen = pen_s + (PREFERENCE_PENALTY_METERS
                                   if preferred and line not in preferred else 0.0)
                new_key = self._key(new_dist, new_trans, new_pen)

                sid = self._state_index.get((nxt, line, new_trans))
                if sid is None:
                    sid = self._add_state(nxt, line, new_trans, new_dist, new_pen,
                                          new_key, s, edge)
                    pq.insert(sid, new_key)
                elif sid not in settled and new_key < self._state_key[sid]:
                    self._state_dist[sid] = new_dist
                    self._state_pen[sid] = new_pen
                    self._state_key[sid] = new_key
                    self._state_prev[sid] = s
                    self._state_edge[sid] = edge
                    pq.decrease_key(sid, new_key)

        # Choose the best state for every station.
        for sid in range(len(self._state_node)):
            node = self._state_node[sid]
            if node not in self._best_state or \
                    self._state_key[sid] < self._state_key[self._best_state[node]]:
                self._best_state[node] = sid
        for node, sid in self._best_state.items():
            self.dist_to[node] = self._state_dist[sid]

    def has_path_to(self, target):
        """Return True if the target station is reachable under the configuration."""
        return target in self._best_state

    def path_with_edges(self, target):
        """
        Reconstruct the path from the source to ``target``.

        Returns:
            tuple: (list of station numbers from source to target,
                    list of Edge objects along the path).
            Both lists are empty if the target is unreachable.
        """
        if target not in self._best_state:
            return [], []
        sid = self._best_state[target]
        nodes = []
        edges = []
        while sid != -1:
            nodes.append(self._state_node[sid])
            if self._state_prev[sid] != -1:
                edges.append(self._state_edge[sid])
            sid = self._state_prev[sid]
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    def get_transfer_count(self, target):
        """Return the number of line changes on the path to ``target``."""
        _, edges = self.path_with_edges(target)
        return count_transfers(edges)
