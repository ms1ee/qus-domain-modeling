"""Data integrity checks and update helpers."""

REQUIRED_LINES = ["Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
                  "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
                  "Fangshan Line", "Airport Line"]


def check_data(data):
    """Return list of problem strings (empty if fine) and info lines."""
    problems = []
    names = {s["name"] for s in data.get("stations", [])}
    lines_present = set()
    for s in data.get("stations", []):
        lines_present.update(s.get("lines", []))
    for c in data.get("connections", []):
        lines_present.add(c.get("line"))
    for ln in REQUIRED_LINES:
        if not any(ln.lower() == p.lower() or ln.lower() in str(p).lower() for p in lines_present):
            problems.append("Missing line coverage: %s" % ln)
    linked = set()
    for c in data.get("connections", []):
        for k in ("source", "dest"):
            if c[k] not in names:
                problems.append("Connection references unknown station: %s" % c[k])
            linked.add(c[k])
        d = c.get("distance")
        if not isinstance(d, (int, float)) or d <= 0:
            problems.append("Invalid distance %s between %s and %s" % (d, c["source"], c["dest"]))
        elif d > 20000:
            problems.append("Suspicious distance %s between %s and %s" % (d, c["source"], c["dest"]))
    for n in names - linked:
        problems.append("Station without connections: %s" % n)
    return problems


def add_line(data, line_name, station_names, distances):
    """Add a new line; distances has len(station_names)-1 entries (meters)."""
    if len(distances) != len(station_names) - 1:
        raise ValueError("distances length mismatch")
    existing = {s["name"]: s for s in data["stations"]}
    for n in station_names:
        if n in existing:
            if line_name not in existing[n]["lines"]:
                existing[n]["lines"].append(line_name)
        else:
            data["stations"].append({"name": n, "lines": [line_name]})
    for i, d in enumerate(distances):
        data["connections"].append({"source": station_names[i], "dest": station_names[i + 1],
                                    "distance": d, "line": line_name})


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
