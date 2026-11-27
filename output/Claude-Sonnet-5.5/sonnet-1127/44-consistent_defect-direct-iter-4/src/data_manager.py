"""Graph construction, integrity checks and data updates."""
from models import Edge, Graph


def build_graph(data):
    """Return (graph, station_to_number, number_to_station)."""
    graph = Graph()
    s2n = {}
    n2s = {}

    def reg(name):
        if name not in s2n:
            s2n[name] = len(s2n)
            n2s[s2n[name]] = name
            graph.add_node(s2n[name])

    for st in data.get("stations", []):
        reg(st["name"])
        graph.set_station_lines(st["name"], st.get("lines", []))
    for c in data.get("connections", []):
        reg(c["source"])
        reg(c["dest"])
        graph.add_edge(Edge(s2n[c["source"]], s2n[c["dest"]], c["distance"], c["line"]))
    for name in s2n:
        if name not in graph.station_lines:
            graph.set_station_lines(name, [])
    return graph, s2n, n2s


def check_data(data):
    """Return list of report lines and an ok flag."""
    report = []
    ok = True
    stations = {s["name"] for s in data.get("stations", [])}
    conns = data.get("connections", [])
    report.append("Stations: %d, connections: %d" % (len(stations), len(conns)))
    if not stations:
        ok = False
        report.append("ERROR: no stations")
    lines = set()
    for s in data.get("stations", []):
        lines.update(s.get("lines", []))
    report.append("Lines: %d" % len(lines))
    bad = [c for c in conns if c["source"] not in stations or c["dest"] not in stations]
    if bad:
        ok = False
        report.append("ERROR: %d connections reference unknown stations" % len(bad))
    badd = [c for c in conns if not isinstance(c["distance"], (int, float)) or c["distance"] <= 0]
    if badd:
        ok = False
        report.append("ERROR: %d connections with invalid distance" % len(badd))
    connected = set()
    for c in conns:
        connected.add(c["source"])
        connected.add(c["dest"])
    iso = stations - connected
    if iso:
        report.append("WARNING: %d stations without connections" % len(iso))
    cline = {c["line"] for c in conns}
    missing = lines - cline
    if missing:
        report.append("WARNING: lines without connections: %s" % ", ".join(sorted(missing)))
    report.append("Data check " + ("passed" if ok else "FAILED"))
    return report, ok


def add_line(data, line_name, station_names, distances):
    """Add a new line: consecutive stations with bidirectional connections."""
    if len(distances) != len(station_names) - 1:
        raise ValueError("distances must have len(stations)-1 items")
    existing = {s["name"]: s for s in data["stations"]}
    for n in station_names:
        if n in existing:
            if line_name not in existing[n]["lines"]:
                existing[n]["lines"].append(line_name)
        else:
            s = {"name": n, "lines": [line_name]}
            data["stations"].append(s)
            existing[n] = s
    for a, b, d in zip(station_names, station_names[1:], distances):
        data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
        data["connections"].append({"source": b, "dest": a, "distance": d, "line": line_name})


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


def update_distance(data, a, b, distance, line=None, both=True):
    n = 0
    for c in data["connections"]:
        if line is not None and c["line"] != line:
            continue
        if (c["source"] == a and c["dest"] == b) or (both and c["source"] == b and c["dest"] == a):
            c["distance"] = distance
            n += 1
    return n
