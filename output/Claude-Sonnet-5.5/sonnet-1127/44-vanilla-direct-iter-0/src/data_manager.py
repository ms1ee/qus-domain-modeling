"""Network construction, integrity checks and data updates."""
from models import Edge, Graph

REPRESENTATIVE = {
    "Line 1": ["Tiananmen East"],
}


def build_graph(data):
    """Return (graph, station_to_number, number_to_station)."""
    graph = Graph()
    s2n = {}
    n2s = {}
    for st in data.get("stations", []):
        if st["name"] not in s2n:
            n = len(s2n)
            s2n[st["name"]] = n
            n2s[n] = st["name"]
            graph.add_node(n)
        graph.set_station_lines(st["name"], st.get("lines", []))
    for c in data.get("connections", []):
        for nm in (c["source"], c["dest"]):
            if nm not in s2n:
                n = len(s2n)
                s2n[nm] = n
                n2s[n] = nm
                graph.add_node(n)
                graph.set_station_lines(nm, [c["line"]])
        graph.add_edge(Edge(s2n[c["source"]], s2n[c["dest"]], c["distance"], c["line"]))
    return graph, s2n, n2s


def check_data(data):
    """Return list of problem strings (empty if OK)."""
    problems = []
    names = set()
    for st in data.get("stations", []):
        if not st.get("name"):
            problems.append("Station without name")
        if not st.get("lines"):
            problems.append("Station %s has no lines" % st.get("name"))
        names.add(st.get("name"))
    if not names:
        problems.append("No stations")
    linked = set()
    for c in data.get("connections", []):
        for k in ("source", "dest"):
            if c[k] not in names:
                problems.append("Connection references unknown station %s" % c[k])
            linked.add(c[k])
        d = c.get("distance")
        if not isinstance(d, (int, float)) or d <= 0:
            problems.append("Bad distance %s-%s: %r" % (c["source"], c["dest"], d))
        elif d > 20000:
            problems.append("Suspicious distance %s-%s: %r" % (c["source"], c["dest"], d))
        if c["source"] == c["dest"]:
            problems.append("Self loop at %s" % c["source"])
    for n in names - linked:
        problems.append("Station %s has no connections" % n)
    lines = set()
    for st in data.get("stations", []):
        lines.update(st.get("lines", []))
    for c in data.get("connections", []):
        lines.add(c["line"])
    for ln, sts in REPRESENTATIVE.items():
        if ln in lines:
            for s in sts:
                if s not in names:
                    problems.append("Representative station %s missing on %s" % (s, ln))
    return problems


def add_line(data, line_name, station_names, distances):
    """Add a new line; distances has len(station_names)-1 entries."""
    if len(distances) != len(station_names) - 1:
        raise ValueError("distances length mismatch")
    existing = {s["name"]: s for s in data["stations"]}
    for nm in station_names:
        if nm in existing:
            if line_name not in existing[nm]["lines"]:
                existing[nm]["lines"].append(line_name)
        else:
            s = {"name": nm, "lines": [line_name]}
            data["stations"].append(s)
            existing[nm] = s
    for a, b, d in zip(station_names, station_names[1:], distances):
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


def update_distance(data, a, b, distance, line=None):
    ok = False
    for c in data["connections"]:
        if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
            c["distance"] = distance
            ok = True
    return ok
