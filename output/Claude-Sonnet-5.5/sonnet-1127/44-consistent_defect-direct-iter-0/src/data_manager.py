"""Data integrity checks and update helpers."""


def check_data(data):
    """Return list of problem strings (empty if OK)."""
    problems = []
    names = {s["name"] for s in data.get("stations", [])}
    if not names:
        problems.append("No stations found")
    lines = set()
    for s in data.get("stations", []):
        lines.update(s.get("lines", []))
    connected = set()
    for c in data.get("connections", []):
        for k in ("source", "dest"):
            if c[k] not in names:
                problems.append("Connection references unknown station: %s" % c[k])
        d = c.get("distance")
        if not isinstance(d, (int, float)) or d <= 0:
            problems.append("Invalid distance %s->%s: %r" % (c["source"], c["dest"], d))
        connected.add(c["source"])
        connected.add(c["dest"])
    for n in sorted(names - connected):
        problems.append("Station without connections: %s" % n)
    return problems


def add_line(data, line, station_names, distances):
    """Add a line with consecutive stations (both directions)."""
    known = {s["name"]: s for s in data["stations"]}
    for n in station_names:
        if n in known:
            if line not in known[n]["lines"]:
                known[n]["lines"].append(line)
        else:
            s = {"name": n, "lines": [line]}
            data["stations"].append(s)
            known[n] = s
    for i in range(len(station_names) - 1):
        a, b, d = station_names[i], station_names[i + 1], distances[i]
        data["connections"].append({"source": a, "dest": b, "distance": d, "line": line})
        data["connections"].append({"source": b, "dest": a, "distance": d, "line": line})


def update_station(data, name, lines=None, new_name=None):
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
    n = 0
    for c in data["connections"]:
        if c["source"] == a and c["dest"] == b and (line is None or c["line"] == line):
            c["distance"] = distance
            n += 1
    return n
