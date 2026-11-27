"""Data integrity checks and update helpers."""


def check_data(data):
    """Return (ok, list of messages)."""
    problems = []
    stations = data.get("stations", [])
    conns = data.get("connections", [])
    names = [s["name"] for s in stations]
    if len(names) != len(set(names)):
        problems.append("Duplicate station names found")
    nameset = set(names)
    lines = set()
    linked = set()
    for s in stations:
        lines.update(s.get("lines", []))
    for c in conns:
        for k in ("source", "dest"):
            if c[k] not in nameset:
                problems.append("Connection references unknown station '%s'" % c[k])
        d = c.get("distance")
        if not isinstance(d, (int, float)) or d <= 0:
            problems.append("Invalid distance %r between %s and %s" % (d, c["source"], c["dest"]))
        elif d > 30000:
            problems.append("Suspicious distance %r between %s and %s" % (d, c["source"], c["dest"]))
        linked.add(c["source"])
        linked.add(c["dest"])
    for n in names:
        if n not in linked:
            problems.append("Station '%s' has no connections" % n)
    return (not problems), problems + [
        "Stations: %d, connections: %d, lines: %d" % (len(names), len(conns), len(lines))]


def add_line(data, line, station_names, distances):
    """Add a line; distances has len(station_names)-1 entries."""
    if len(distances) != len(station_names) - 1:
        raise ValueError("distances must have one fewer entry than stations")
    index = {s["name"]: s for s in data["stations"]}
    for n in station_names:
        if n in index:
            if line not in index[n]["lines"]:
                index[n]["lines"].append(line)
        else:
            st = {"name": n, "lines": [line]}
            data["stations"].append(st)
            index[n] = st
    for i, d in enumerate(distances):
        data["connections"].append(
            {"source": station_names[i], "dest": station_names[i + 1], "distance": int(d), "line": line})


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
