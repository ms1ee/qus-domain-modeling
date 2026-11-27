"""Data management and integrity checks."""
import json
from data_loader import DATA_FILE_PATH, load_subway_data
from network import SubwayNetwork

REPRESENTATIVE = {"1号线": ["西单", "国贸"], "2号线": ["西直门", "雍和宫"], "Line 1": ["Xidan"]}


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)

    def network(self):
        return SubwayNetwork(self.data_file, data=self.data)

    def add_line(self, line, stations, distances):
        """stations: ordered names; distances: meters between consecutive ones (both directions)."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have len(stations)-1 items")
        known = {s["name"]: s for s in self.data["stations"]}
        for n in stations:
            if n in known:
                if line not in known[n]["lines"]:
                    known[n]["lines"].append(line)
            else:
                self.data["stations"].append({"name": n, "lines": [line]})
        for a, b, d in zip(stations, stations[1:], distances):
            for s, t in ((a, b), (b, a)):
                self.data["connections"].append({"source": s, "dest": t, "distance": d, "line": line})

    def update_station(self, name, new_name=None, lines=None):
        for s in self.data["stations"]:
            if s["name"] == name:
                if lines is not None:
                    s["lines"] = list(lines)
                if new_name:
                    s["name"] = new_name
                    for c in self.data["connections"]:
                        if c["source"] == name:
                            c["source"] = new_name
                        if c["dest"] == name:
                            c["dest"] = new_name
                return True
        return False

    def update_distance(self, a, b, distance, bidirectional=True):
        n = 0
        for c in self.data["connections"]:
            if (c["source"], c["dest"]) == (a, b) or (bidirectional and (c["source"], c["dest"]) == (b, a)):
                c["distance"] = distance
                n += 1
        return n

    def save(self, path=None):
        with open(path or self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)


class DataIntegrityChecker:
    def __init__(self, manager):
        self.manager = manager

    def check(self):
        """Return list of problem strings (empty if OK)."""
        d = self.manager.data
        problems = []
        names = set()
        for s in d.get("stations", []):
            if s["name"] in names:
                problems.append("Duplicate station: %s" % s["name"])
            names.add(s["name"])
            if not s.get("lines"):
                problems.append("Station without line: %s" % s["name"])
        if len(names) < 50:
            problems.append("Station coverage too small: %d" % len(names))
        pairs = set()
        for c in d.get("connections", []):
            for k in ("source", "dest"):
                if c[k] not in names:
                    problems.append("Connection references unknown station: %s" % c[k])
            if not isinstance(c.get("distance"), (int, float)) or c["distance"] <= 0:
                problems.append("Bad distance: %s -> %s" % (c["source"], c["dest"]))
            elif c["distance"] > 30000:
                problems.append("Suspicious distance: %s -> %s" % (c["source"], c["dest"]))
            pairs.add((c["source"], c["dest"]))
        connected = {p[0] for p in pairs} | {p[1] for p in pairs}
        for n in sorted(names - connected):
            problems.append("Isolated station: %s" % n)
        return problems
