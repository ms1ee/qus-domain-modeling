"""Subway network data management (update mechanisms)."""

from data_loader import (DATA_FILE_PATH, build_graph, load_subway_data,
                         save_subway_data)


class SubwayNetwork:
    """Manages stations, connections and lines; supports data updates."""

    def __init__(self, data=None, data_source=DATA_FILE_PATH):
        self.data_source = data_source
        self.data = data if data is not None else load_subway_data(data_source)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    # ----- queries -----
    def station_names(self):
        return [s["name"] for s in self.data["stations"]]

    def find_station(self, name):
        for s in self.data["stations"]:
            if s["name"] == name:
                return s
        return None

    def lines(self):
        """Return dict line name -> ordered station sequence."""
        result = {}
        for s in self.data["stations"]:
            for l in s.get("lines", []):
                result.setdefault(l, [])
        for c in self.data["connections"]:
            seq = result.setdefault(c.get("line"), [])
            for nm in (c["source"], c["dest"]):
                if nm not in seq:
                    seq.append(nm)
        return result

    def transfer_stations(self):
        return [s["name"] for s in self.data["stations"] if len(s.get("lines", [])) > 1]

    def build_graph(self):
        return build_graph(self.data)

    # ----- updates -----
    def add_station(self, name, lines):
        st = self.find_station(name)
        if st is None:
            self.data["stations"].append({"name": name, "lines": list(lines)})
        else:
            for l in lines:
                if l not in st["lines"]:
                    st["lines"].append(l)

    def add_line(self, line_name, stations, distances, bidirectional=True):
        """Add a new line: ``stations`` ordered, ``distances`` between neighbours."""
        if len(distances) != max(len(stations) - 1, 0):
            raise ValueError("distances must have len(stations) - 1 entries")
        for nm in stations:
            self.add_station(nm, [line_name])
        for a, b, d in zip(stations, stations[1:], distances):
            if d <= 0:
                raise ValueError("distance must be positive")
            self.data["connections"].append(
                {"source": a, "dest": b, "distance": int(d), "line": line_name})
            if bidirectional:
                self.data["connections"].append(
                    {"source": b, "dest": a, "distance": int(d), "line": line_name})

    def update_station(self, name, new_name=None, lines=None):
        st = self.find_station(name)
        if st is None:
            raise KeyError(f"Station '{name}' does not exist")
        if lines is not None:
            st["lines"] = list(lines)
        if new_name and new_name != name:
            st["name"] = new_name
            for c in self.data["connections"]:
                if c["source"] == name:
                    c["source"] = new_name
                if c["dest"] == name:
                    c["dest"] = new_name

    def update_distance(self, source, dest, distance, line=None, both_directions=True):
        if distance <= 0:
            raise ValueError("distance must be positive")
        count = 0
        for c in self.data["connections"]:
            if line is not None and c.get("line") != line:
                continue
            if (c["source"], c["dest"]) == (source, dest) or \
                    (both_directions and (c["source"], c["dest"]) == (dest, source)):
                c["distance"] = int(distance)
                count += 1
        if count == 0:
            raise KeyError(f"No connection between '{source}' and '{dest}'")
        return count

    def save(self, path=None):
        save_subway_data(self.data, path or self.data_source)
