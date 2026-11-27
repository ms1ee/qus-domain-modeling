"""
Data update utilities for the subway dataset.

All functions operate on the in-memory dataset dictionary (as returned by
``data_loader.load_subway_data``); ``save_subway_data`` persists changes.
"""

import json

from data_loader import DATA_FILE_PATH


def _find_station(data, name):
    for entry in data["stations"]:
        if entry.get("name") == name:
            return entry
    return None


def _line_exists(data, line_name):
    if any(line_name in entry.get("lines", []) for entry in data["stations"]):
        return True
    return any(conn.get("line") == line_name for conn in data["connections"])


def _validate_distance(distance):
    if not isinstance(distance, int) or isinstance(distance, bool) or distance <= 0:
        raise ValueError("distance must be a positive integer number of meters")


def add_line(data, line_name, station_names, connections):
    """
    Add a new line with its stations and connections.

    Args:
        data: The dataset dictionary (modified in place).
        line_name: Name of the new line.
        station_names: Ordered list of station names on the line. Existing
                       stations gain the new line; unknown ones are created.
        connections: List of dicts with ``source``, ``dest`` and ``distance``
                     (meters). Endpoints must be in ``station_names``.

    Returns:
        dict: The updated dataset.

    Raises:
        ValueError: On invalid or duplicate input.
    """
    line_name = str(line_name).strip()
    if not line_name:
        raise ValueError("line name cannot be empty")
    if _line_exists(data, line_name):
        raise ValueError(f"line '{line_name}' already exists")

    stations = []
    for name in station_names:
        cleaned = str(name).strip()
        if cleaned and cleaned not in stations:
            stations.append(cleaned)
    if len(stations) < 2:
        raise ValueError("a line needs at least two stations")

    for name in stations:
        entry = _find_station(data, name)
        if entry is None:
            data["stations"].append({"name": name, "lines": [line_name]})
        elif line_name not in entry.setdefault("lines", []):
            entry["lines"].append(line_name)

    for conn in connections:
        source = str(conn["source"]).strip()
        dest = str(conn["dest"]).strip()
        if source not in stations or dest not in stations:
            raise ValueError(f"connection {source} - {dest} references stations outside the line")
        _validate_distance(conn["distance"])
        data["connections"].append({
            "source": source,
            "dest": dest,
            "distance": conn["distance"],
            "line": line_name,
        })
    return data


def modify_station(data, name, new_name=None, lines=None):
    """
    Modify a station's name and/or lines.

    Renaming also updates every connection that references the station.

    Raises:
        KeyError: If the station does not exist.
        ValueError: If the new name is already taken.
    """
    entry = _find_station(data, name)
    if entry is None:
        raise KeyError(f"station '{name}' does not exist")

    if lines is not None:
        entry["lines"] = list(dict.fromkeys(str(line) for line in lines))

    if new_name is not None and new_name != name:
        new_name = str(new_name).strip()
        if not new_name:
            raise ValueError("new station name cannot be empty")
        if _find_station(data, new_name) is not None:
            raise ValueError(f"station '{new_name}' already exists")
        entry["name"] = new_name
        for conn in data["connections"]:
            if conn.get("source") == name:
                conn["source"] = new_name
            if conn.get("dest") == name:
                conn["dest"] = new_name
    return entry


def update_distance(data, source, dest, distance, line=None):
    """
    Update the distance of the connection(s) between two stations.

    Args:
        line: If given, only the connection on this line is updated.

    Returns:
        int: Number of connections updated.

    Raises:
        KeyError: If no matching connection exists.
        ValueError: If the distance is not a positive integer.
    """
    _validate_distance(distance)
    matches = [
        conn for conn in data["connections"]
        if {conn.get("source"), conn.get("dest")} == {source, dest}
        and (line is None or conn.get("line") == line)
    ]
    if not matches:
        raise KeyError(f"no connection between '{source}' and '{dest}'")
    for conn in matches:
        conn["distance"] = distance
    return len(matches)


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write the dataset back to a JSON file (UTF-8, indented)."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path
