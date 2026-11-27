"""Graph building, integrity check and data update helpers."""
from models import Graph, Edge


def build_graph(data):
    g = Graph()
    for s in data.get("stations", []):
        g.add_station(s["name"])
        g.set_station_lines(s["name"], s.get("lines", []))
    for c in data.get("connections", []):
        a = g.add_station(c["source"])
        b = g.add_station(c["dest"])
        for n in (c["source"], c["dest"]):
            lines = g.station_lines.setdefault(n, [])
            if c["line"] not in lines:
                lines.append(c["line"])
        g.add_edge(Edge(a, b, c["distance"], c["line"]))
    return g


def check_data(data):
    """Return (ok, list of messages)."""
    msgs = []
    stations = data.get("stations", [])
    conns = data.get("connections", [])
    names = {s["name"] for s in stations}
    if not stations:
        msgs.append("No stations found")
    if len(names) != len(stations):
        msgs.append("Duplicate station names found")
    lines = {c["line"] for c in conns}
    if not lines:
        msgs.append("No lines found")
    connected = set()
    for c in conns:
        if c["source"] not in names or c["dest"] not in names:
            msgs.append(f"Connection references unknown station: {c['source']} - {c['dest']}")
        if c["source"] == c["dest"]:
            msgs.append(f"Self connection: {c['source']}")
        d = c.get("distance")
        if not isinstance(d, (int, float)) or d <= 0 or d > 30000:
            msgs.append(f"Suspicious distance {d}: {c['source']} - {c['dest']} ({c['line']})")
        connected.add(c["source"])
        connected.add(c["dest"])
    for n in names - connected:
        msgs.append(f"Station without connections: {n}")
    return (not msgs), msgs


def add_line(data, line_name, station_names, distances):
    """Add a new line: consecutive stations with given distances."""
    if len(distances) != len(station_names) - 1:
        raise ValueError("distances must have len(stations)-1 entries")
    existing = {s["name"]: s for s in data["stations"]}
    for n in station_names:
        if n in existing:
            if line_name not in existing[n]["lines"]:
                existing[n]["lines"].append(line_name)
        else:
            data["stations"].append({"name": n, "lines": [line_name]})
    for i, d in enumerate(distances):
        data["connections"].append({"source": station_names[i], "dest": station_names[i + 1],
                                    "distance": int(d), "line": line_name})


def update_station(data, old_name, new_name=None, lines=None):
    for s in data["stations"]:
        if s["name"] == old_name:
            if lines is not None:
                s["lines"] = list(lines)
            if new_name:
                s["name"] = new_name
                for c in data["connections"]:
                    if c["source"] == old_name:
                        c["source"] = new_name
                    if c["dest"] == old_name:
                        c["dest"] = new_name
            return True
    return False


def update_distance(data, a, b, distance, line=None):
    found = False
    for c in data["connections"]:
        if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
            c["distance"] = int(distance)
            found = True
    return found
