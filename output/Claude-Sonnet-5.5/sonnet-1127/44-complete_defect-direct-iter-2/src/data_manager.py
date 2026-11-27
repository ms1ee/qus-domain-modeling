"""Data integrity checks and update helpers."""

REPRESENTATIVE = {
    "Line 1": None, "Line 2": None, "Line 4": None, "Line 5": None,
}


def check_data(data):
    """Return list of problem strings (empty if OK)."""
    problems = []
    stations = {s["name"]: s for s in data.get("stations", [])}
    if not stations:
        problems.append("No stations")
    lines = set()
    for s in stations.values():
        lines.update(s.get("lines", []))
    if not lines:
        problems.append("No lines found")
    deg = {n: 0 for n in stations}
    for c in data.get("connections", []):
        for k in ("source", "dest"):
            if c[k] not in stations:
                problems.append("Connection references unknown station: %s" % c[k])
            else:
                deg[c[k]] += 1
        d = c.get("distance")
        if not isinstance(d, (int, float)) or d <= 0:
            problems.append("Bad distance %s-%s: %r" % (c["source"], c["dest"], d))
        elif d > 30000:
            problems.append("Suspicious distance %s-%s: %r" % (c["source"], c["dest"], d))
    for n, k in deg.items():
        if k == 0:
            problems.append("Isolated station: %s" % n)
    return problems


def add_line(data, line_name, station_names, distances):
    """Add a new line; distances has len(station_names)-1 entries."""
    if len(distances) != len(station_names) - 1:
        raise ValueError("distances length mismatch")
    index = {s["name"]: s for s in data["stations"]}
    for n in station_names:
        if n in index:
            if line_name not in index[n]["lines"]:
                index[n]["lines"].append(line_name)
        else:
            s = {"name": n, "lines": [line_name]}
            data["stations"].append(s)
            index[n] = s
    for a, b, d in zip(station_names, station_names[1:], distances):
        data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})


def modify_station(data, name, new_name=None, lines=None):
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
