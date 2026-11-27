"""Data integrity checks and update mechanisms."""
from models import Edge, Graph

REPRESENTATIVE = {
    "Line 1": "Tiananmen East", "Line 2": "Xizhimen", "Line 4": "Xidan",
    "Line 5": "Dongdan", "Line 10": "Guomao", "Line 13": "Wudaokou",
}


def build_graph(data):
    """Return (graph, station_to_number, number_to_station)."""
    s2n, n2s = {}, {}
    g = Graph()

    def reg(name):
        if name not in s2n:
            num = len(s2n) + 1
            s2n[name] = num
            n2s[num] = name
            g.add_node(num)
        return s2n[name]

    for st in data.get("stations", []):
        reg(st["name"])
        g.set_station_lines(st["name"], st.get("lines", []))
    for c in data.get("connections", []):
        a, b = reg(c["source"]), reg(c["dest"])
        g.add_edge(Edge(a, b, c["distance"], c["line"]))
        for name in (c["source"], c["dest"]):
            lines = g.station_lines.setdefault(name, [])
            if c["line"] not in lines:
                lines.append(c["line"])
    return g, s2n, n2s


def check_data(data):
    """Return list of problem strings (empty if OK)."""
    problems = []
    names = {s["name"] for s in data.get("stations", [])}
    if not names:
        problems.append("No stations")
    for line, st in REPRESENTATIVE.items():
        if st not in names:
            problems.append("Representative station missing: %s (%s)" % (st, line))
    linked = set()
    for c in data.get("connections", []):
        linked.add(c["source"])
        linked.add(c["dest"])
        for k in ("source", "dest"):
            if c[k] not in names:
                problems.append("Connection references unknown station: %s" % c[k])
        d = c.get("distance")
        if not isinstance(d, (int, float)) or d <= 0:
            problems.append("Invalid distance %s-%s: %r" % (c["source"], c["dest"], d))
        elif d > 30000:
            problems.append("Suspicious distance %s-%s: %s" % (c["source"], c["dest"], d))
    for n in sorted(names - linked):
        problems.append("Station without connections: %s" % n)
    return problems


def add_line(data, line_name, stations, distances):
    """Add a line; stations is an ordered list, distances has len-1 entries."""
    if len(distances) != len(stations) - 1:
        raise ValueError("distances must have len(stations)-1 entries")
    known = {s["name"]: s for s in data["stations"]}
    for n in stations:
        if n in known:
            if line_name not in known[n]["lines"]:
                known[n]["lines"].append(line_name)
        else:
            s = {"name": n, "lines": [line_name]}
            data["stations"].append(s)
            known[n] = s
    for a, b, d in zip(stations, stations[1:], distances):
        data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})


def update_station(data, name, new_name=None, lines=None):
    for s in data["stations"]:
        if s["name"] == name:
            if lines is not None:
                s["lines"] = list(lines)
            if new_name:
                s["name"] = new_name
                for c in data["connections"]:
                    if c["source"] == name:
                        c["source"] = new_name
                    if c["dest"] == name:
                        c["dest"] = new_name
            return True
    return False


def update_distance(data, a, b, distance):
    ok = False
    for c in data["connections"]:
        if {c["source"], c["dest"]} == {a, b}:
            c["distance"] = distance
            ok = True
    return ok
