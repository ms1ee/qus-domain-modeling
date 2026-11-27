"""Data integrity checks and update mechanisms."""

REPRESENTATIVE = {
    "Line 1": ["苹果园", "国贸", "四惠"],
    "Line 2": ["西直门", "建国门"],
    "Line 4": ["安河桥北", "宣武门"],
    "Line 5": ["天通苑北", "宋家庄"],
    "Line 10": ["知春路", "劲松"],
    "Line 13": ["西直门", "东直门"],
}


def check_data(data):
    """Return (ok, list of messages)."""
    msgs = []
    names = {s["name"] for s in data.get("stations", [])}
    if not names:
        msgs.append("No stations found")
    for line, sts in REPRESENTATIVE.items():
        for s in sts:
            if s not in names:
                msgs.append("Warning: representative station '%s' (%s) missing" % (s, line))
    adj = {}
    lines_of = {s["name"]: set(s.get("lines", [])) for s in data.get("stations", [])}
    for c in data.get("connections", []):
        a, b, d = c.get("source"), c.get("dest"), c.get("distance")
        if a not in names or b not in names:
            msgs.append("Connection endpoint missing: %s - %s" % (a, b))
            continue
        if not isinstance(d, (int, float)) or d <= 0:
            msgs.append("Invalid distance %s between %s and %s" % (d, a, b))
        if c.get("line") not in lines_of.get(a, set()) or c.get("line") not in lines_of.get(b, set()):
            msgs.append("Line %s not listed for %s or %s" % (c.get("line"), a, b))
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    for n in names:
        if n not in adj:
            msgs.append("Station '%s' has no connections" % n)
    if names and adj:
        start = next(iter(adj))
        seen, stack = {start}, [start]
        while stack:
            for m in adj[stack.pop()]:
                if m not in seen:
                    seen.add(m)
                    stack.append(m)
        if len(seen) != len(adj):
            msgs.append("Network not fully connected: %d of %d stations reachable" % (len(seen), len(adj)))
    hard = [m for m in msgs if not m.startswith("Warning")]
    return (not hard), msgs


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
                                    "distance": int(d), "line": line_name})


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
            c["distance"] = int(distance)
            ok = True
    return ok
