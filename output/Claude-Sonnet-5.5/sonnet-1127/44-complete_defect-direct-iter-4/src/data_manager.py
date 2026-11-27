"""Network construction, integrity checks and data updates."""
from models import Edge, Graph

REPRESENTATIVE = {
    "1号线": [], "2号线": [], "4号线": [], "5号线": [], "6号线": [], "8号线": [],
    "10号线": [], "13号线": [], "14号线": [], "15号线": [],
}


def build_network(data):
    """Return (graph, station_to_number, number_to_station)."""
    graph = Graph()
    s2n, n2s = {}, {}
    for st in data.get("stations", []):
        name = st["name"]
        if name not in s2n:
            s2n[name] = len(s2n)
            n2s[s2n[name]] = name
            graph.add_node(s2n[name])
        graph.set_station_lines(name, st.get("lines", []))
    for c in data.get("connections", []):
        for nm in (c["source"], c["dest"]):
            if nm not in s2n:
                s2n[nm] = len(s2n)
                n2s[s2n[nm]] = nm
                graph.add_node(s2n[nm])
                graph.station_lines.setdefault(nm, [c["line"]])
        graph.add_edge(Edge(s2n[c["source"]], s2n[c["dest"]], c["distance"], c["line"]))
    return graph, s2n, n2s


def check_data(data):
    """Return list of problem strings (empty if data is fine) and a summary list."""
    problems = []
    names = {s["name"] for s in data.get("stations", [])}
    if not names:
        problems.append("No station data")
    lines = set()
    for s in data.get("stations", []):
        lines.update(s.get("lines", []))
        if not s.get("lines"):
            problems.append("Station without line: %s" % s["name"])
    for c in data.get("connections", []):
        if c["source"] not in names or c["dest"] not in names:
            problems.append("Connection references unknown station: %s-%s" % (c["source"], c["dest"]))
        d = c.get("distance")
        if not isinstance(d, (int, float)) or d <= 0 or d > 30000:
            problems.append("Suspicious distance %s: %s-%s" % (d, c["source"], c["dest"]))
        if c["source"] == c["dest"]:
            problems.append("Self loop at %s" % c["source"])
    connected = set()
    for c in data.get("connections", []):
        connected.add(c["source"])
        connected.add(c["dest"])
    for n in sorted(names - connected):
        problems.append("Station has no connections: %s" % n)
    for key in REPRESENTATIVE:
        if not any(key in l or l in key for l in lines):
            problems.append("Main line missing: %s" % key)
    summary = ["Stations: %d" % len(names), "Connections: %d" % len(data.get("connections", [])),
               "Lines: %d" % len(lines)]
    return problems, summary


def add_line(data, line_name, stations, distances):
    """Add a new line: stations (ordered names) and distances between neighbours."""
    if len(distances) != len(stations) - 1:
        raise ValueError("distances must have len(stations)-1 items")
    existing = {s["name"]: s for s in data["stations"]}
    for n in stations:
        if n in existing:
            if line_name not in existing[n]["lines"]:
                existing[n]["lines"].append(line_name)
        else:
            data["stations"].append({"name": n, "lines": [line_name]})
    for a, b, d in zip(stations, stations[1:], distances):
        data["connections"].append({"source": a, "dest": b, "distance": int(d), "line": line_name})


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


def update_distance(data, a, b, distance, line=None):
    found = False
    for c in data["connections"]:
        if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
            c["distance"] = int(distance)
            found = True
    return found
