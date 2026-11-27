"""Data loading utilities for the Beijing Subway fare calculation system.

This module is responsible for:

* locating the bundled ``subway_data.json`` file (independent of the current
  working directory),
* loading the raw JSON content,
* building the in-memory network model (station numbering, the ``Graph``
  instance and the ``station_to_number`` mapping),
* station name standardization helpers used by the CLI.
"""

import json
import os
import re

from models import Edge, Graph

# Absolute path of src/subway_data.json, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    :param path: path of the JSON file (defaults to ``DATA_FILE_PATH``)
    :return: the parsed JSON content (a dict)
    :raises FileNotFoundError: if the file does not exist
    :raises ValueError: if the content is not a valid subway data document
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object")
    if "stations" in data and not isinstance(data["stations"], list):
        raise ValueError("'stations' must be a list")
    if "connections" in data and not isinstance(data["connections"], list):
        raise ValueError("'connections' must be a list")
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write subway data back to a JSON file."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def normalize_station_name(name):
    """Standardize a user supplied station name (trim / collapse whitespace)."""
    if name is None:
        return ""
    text = str(name).replace("\u3000", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _loose_key(name):
    """Key used for tolerant matching of station names."""
    text = normalize_station_name(name).lower()
    for suffix in (" station", "站"):
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
    text = text.replace("’", "'").replace("‘", "'")
    return text.strip()


class SubwayNetwork:
    """Container bundling the graph and station numbering maps."""

    def __init__(self, data):
        self.data = data
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self._loose_lookup = {}
        self._build()

    def _register_station(self, name, lines=None):
        name = normalize_station_name(name)
        if not name:
            return None
        if name not in self.station_to_number:
            number = len(self.station_to_number)
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_station(number, name)
            self._loose_lookup.setdefault(_loose_key(name), name)
        if lines is not None:
            existing = self.graph.station_lines.get(name, [])
            merged = list(existing)
            for line in lines:
                if line not in merged:
                    merged.append(line)
            self.graph.set_station_lines(name, merged)
        elif name not in self.graph.station_lines:
            self.graph.set_station_lines(name, [])
        return self.station_to_number[name]

    def _build(self):
        for station in self.data.get("stations", []):
            if not isinstance(station, dict):
                continue
            self._register_station(station.get("name"), list(station.get("lines", []) or []))
        for conn in self.data.get("connections", []):
            if not isinstance(conn, dict):
                continue
            src = self._register_station(conn.get("source"))
            dst = self._register_station(conn.get("dest"))
            if src is None or dst is None or src == dst:
                continue
            distance = conn.get("distance")
            if not isinstance(distance, (int, float)) or isinstance(distance, bool) or distance < 0:
                continue
            line = conn.get("line", "")
            self.graph.add_edge(Edge(src, dst, distance, line))
            # make sure line membership is consistent
            for name in (conn.get("source"), conn.get("dest")):
                name = normalize_station_name(name)
                lines = self.graph.station_lines.get(name, [])
                if line and line not in lines:
                    self.graph.set_station_lines(name, lines + [line])

    def resolve_station(self, name):
        """Return the official station name for user input, or None."""
        text = normalize_station_name(name)
        if not text:
            return None
        if text in self.station_to_number:
            return text
        return self._loose_lookup.get(_loose_key(text))

    def suggest(self, name, limit=3):
        """Return similar station names for a misspelled input."""
        import difflib

        return difflib.get_close_matches(normalize_station_name(name), list(self.station_to_number), n=limit, cutoff=0.6)

    @property
    def lines(self):
        result = []
        for lines in self.graph.station_lines.values():
            for line in lines:
                if line not in result:
                    result.append(line)
        return result


def build_network(data=None):
    """Build a ``SubwayNetwork`` from loaded data (loads default file if None)."""
    if data is None:
        data = load_subway_data(DATA_FILE_PATH)
    return SubwayNetwork(data)
