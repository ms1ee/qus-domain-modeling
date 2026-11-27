"""Subway data management: integrity checks and data updates."""

import json
from collections import deque

from data_loader import DATA_FILE_PATH, build_graph, load_subway_data

MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Representative stations of main lines (English and Chinese alternatives).
REPRESENTATIVE_STATIONS = {
    "Line 1": ["Xidan", "Tian'anmen East", "Guomao", "西单", "天安门东", "国贸"],
    "Line 2": ["Xizhimen", "Dongzhimen", "Beijing Railway Station", "西直门", "东直门", "北京站"],
    "Line 4": ["Xuanwumen", "Zhongguancun", "Beijing South Railway Station", "宣武门", "中关村", "北京南站"],
    "Line 5": ["Dongdan", "Yonghegong", "Tiantongyuan", "东单", "雍和宫", "天通苑"],
    "Line 6": ["Chegongzhuang", "Dongsi", "Caofang", "车公庄", "东四", "草房"],
    "Line 8": ["Gulou Dajie", "Olympic Green", "Huoying", "鼓楼大街", "奥林匹克公园", "霍营"],
    "Line 10": ["Haidian Huangzhuang", "Sanyuanqiao", "Jinsong", "海淀黄庄", "三元桥", "劲松"],
    "Line 13": ["Xizhimen", "Huilongguan", "Wangjing West", "西直门", "回龙观", "望京西"],
    "Line 14": ["Wangjing", "Jintai Lu", "Beijing South Railway Station", "望京", "金台路", "北京南站"],
    "Line 15": ["Wangjing", "Olympic Green", "Qinghuadongluxikou", "望京", "奥林匹克公园", "清华东路西口"],
    "Changping Line": ["Xi'erqi", "Zhuxinzhuang", "Changping", "西二旗", "朱辛庄", "昌平"],
    "Yizhuang Line": ["Songjiazhuang", "Yizhuang Railway Station", "宋家庄", "亦庄火车站"],
    "Fangshan Line": ["Guogongzhuang", "Liangxiang University Town", "郭公庄", "良乡大学城"],
    "Airport Line": ["Dongzhimen", "Sanyuanqiao", "Terminal 3", "东直门", "三元桥", "3号航站楼"],
}

MIN_REASONABLE_DISTANCE = 100
MAX_REASONABLE_DISTANCE = 30000


def _norm_line(name):
    return "".join(str(name).lower().split())


class IntegrityReport:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

    @property
    def ok(self):
        return not self.errors

    def format(self):
        out = ["Data integrity check report", "=" * 60]
        for item in self.info:
            out.append("[INFO] " + item)
        for item in self.warnings:
            out.append("[WARNING] " + item)
        for item in self.errors:
            out.append("[ERROR] " + item)
        out.append("=" * 60)
        out.append("Result: %s (%d error(s), %d warning(s))" % (
            "PASSED" if self.ok else "FAILED", len(self.errors), len(self.warnings)))
        return "\n".join(out)


class SubwayDataManager:
    """Manage stations, connections and lines of the subway network."""

    def __init__(self, data=None, path=DATA_FILE_PATH):
        self.path = path
        if data is None:
            data = load_subway_data(path)
        self.data = data
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    @property
    def stations(self):
        return self.data["stations"]

    @property
    def connections(self):
        return self.data["connections"]

    # ---- queries --------------------------------------------------------
    def get_station(self, name):
        for s in self.stations:
            if s.get("name") == name:
                return s
        return None

    def station_names(self):
        return [s.get("name") for s in self.stations]

    def get_lines(self):
        """Map line name -> list of station names (sequence order when possible)."""
        names = []
        for s in self.stations:
            for line in s.get("lines", []) or []:
                if line not in names:
                    names.append(line)
        for c in self.connections:
            if c.get("line") not in names and c.get("line") is not None:
                names.append(c.get("line"))
        return {line: self.get_line_sequence(line) for line in names}

    def get_line_sequence(self, line):
        adj = {}
        order = []
        for c in self.connections:
            if c.get("line") != line:
                continue
            a, b = c.get("source"), c.get("dest")
            for x in (a, b):
                if x not in adj:
                    adj[x] = []
                    order.append(x)
            if b not in adj[a]:
                adj[a].append(b)
            if a not in adj[b]:
                adj[b].append(a)
        if not adj:
            return [s["name"] for s in self.stations if line in (s.get("lines") or [])]
        ends = [x for x in order if len(adj[x]) == 1]
        start = ends[0] if ends else order[0]
        seq, seen, stack = [], set(), [start]
        while stack:
            v = stack.pop()
            if v in seen:
                continue
            seen.add(v)
            seq.append(v)
            for w in reversed(adj[v]):
                if w not in seen:
                    stack.append(w)
        for x in order:
            if x not in seen:
                seq.append(x)
        return seq

    def build_graph(self):
        return build_graph(self.data)

    # ---- updates --------------------------------------------------------
    def add_station(self, name, lines):
        if not name:
            raise ValueError("Station name cannot be empty")
        st = self.get_station(name)
        if st is None:
            self.stations.append({"name": name, "lines": list(lines)})
        else:
            for line in lines:
                if line not in st.setdefault("lines", []):
                    st["lines"].append(line)

    def add_line(self, line_name, station_names, distances):
        """Add a new line given its ordered stations and inter-station distances."""
        if not line_name:
            raise ValueError("Line name cannot be empty")
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must be number of stations minus one")
        for d in distances:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError("Distances must be positive numbers")
        for name in station_names:
            self.add_station(name, [line_name])
        for a, b, d in zip(station_names, station_names[1:], distances):
            self.connections.append({"source": a, "dest": b, "distance": int(d), "line": line_name})

    def modify_station(self, name, new_name=None, lines=None):
        st = self.get_station(name)
        if st is None:
            raise KeyError("Station '%s' does not exist" % name)
        if new_name and new_name != name:
            if self.get_station(new_name) is not None:
                raise ValueError("Station '%s' already exists" % new_name)
            st["name"] = new_name
            for c in self.connections:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name
        if lines is not None:
            st["lines"] = list(lines)

    def update_distance(self, station_a, station_b, distance, line=None):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        count = 0
        for c in self.connections:
            pair = {c.get("source"), c.get("dest")}
            if pair == {station_a, station_b} and (line is None or c.get("line") == line):
                c["distance"] = int(distance)
                count += 1
        if count == 0:
            raise KeyError("No connection between '%s' and '%s'" % (station_a, station_b))
        return count

    def save(self, path=None):
        with open(path or self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)

    # ---- integrity ------------------------------------------------------
    def check_integrity(self):
        rep = IntegrityReport()
        names = {}
        for i, s in enumerate(self.stations):
            name = s.get("name")
            if not name:
                rep.errors.append("Station record #%d has no name" % i)
                continue
            if name in names:
                rep.warnings.append("Duplicate station record: '%s'" % name)
            names[name] = s.get("lines", []) or []
            if not names[name]:
                rep.warnings.append("Station '%s' has no line information" % name)
        rep.info.append("Stations: %d, connections: %d" % (len(names), len(self.connections)))

        # connections
        seen_pairs = set()
        adjacency = {n: set() for n in names}
        for i, c in enumerate(self.connections):
            a, b, d, line = c.get("source"), c.get("dest"), c.get("distance"), c.get("line")
            label = "Connection #%d (%s - %s, %s)" % (i, a, b, line)
            if a not in names or b not in names:
                rep.errors.append("%s references an unknown station" % label)
                continue
            if a == b:
                rep.errors.append("%s is a self-loop" % label)
                continue
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                rep.errors.append("%s has invalid distance %r" % (label, d))
            elif d < MIN_REASONABLE_DISTANCE or d > MAX_REASONABLE_DISTANCE:
                rep.warnings.append("%s has suspicious distance %r m" % (label, d))
            key = (frozenset((a, b)), line)
            if key in seen_pairs:
                rep.warnings.append("%s is duplicated" % label)
            seen_pairs.add(key)
            for x in (a, b):
                if line is not None and names.get(x) and line not in names[x]:
                    rep.warnings.append("%s: station '%s' is not listed on line '%s'" % (label, x, line))
            adjacency[a].add(b)
            adjacency[b].add(a)

        isolated = [n for n, nb in adjacency.items() if not nb]
        for n in isolated:
            rep.errors.append("Station '%s' has no connections" % n)

        # connectivity
        if names:
            start = next(iter(names))
            seen = {start}
            dq = deque([start])
            while dq:
                v = dq.popleft()
                for w in adjacency.get(v, ()):
                    if w not in seen:
                        seen.add(w)
                        dq.append(w)
            if len(seen) < len(names):
                rep.warnings.append("Network is not fully connected: %d of %d stations reachable from '%s'"
                                    % (len(seen), len(names), start))
            else:
                rep.info.append("Network is fully connected")

        # line coverage
        lines = self.get_lines()
        norm_lines = {_norm_line(l): l for l in lines}
        for main in MAIN_LINES:
            actual = norm_lines.get(_norm_line(main))
            if actual is None:
                rep.warnings.append("Main line '%s' not found in data" % main)
                continue
            seq = lines[actual]
            total = sum(c.get("distance", 0) or 0 for c in self.connections
                        if c.get("line") == actual and isinstance(c.get("distance"), (int, float)))
            rep.info.append("%s: %d stations, %.2f km" % (actual, len(seq), total / 1000.0))
            reps = REPRESENTATIVE_STATIONS.get(main, [])
            found = [r for r in reps if r in names]
            if reps and not found:
                rep.warnings.append("No representative station found for '%s'" % main)
        return rep
