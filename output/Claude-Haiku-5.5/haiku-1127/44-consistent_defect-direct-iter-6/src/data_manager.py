"""Data management: integrity checks and update operations on the dataset.

All update functions operate on the raw dataset dictionary returned by
``data_loader.load_subway_data``. Use ``save_subway_data`` to persist changes.
"""

import json
import os
import re
import tempfile

from data_loader import DATA_FILE_PATH

REQUIRED_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

REPRESENTATIVE_STATIONS = [
    "Xizhimen", "Dongzhimen", "Dongdan", "Fuxingmen", "Zhichunlu",
]

MIN_PLAUSIBLE_DISTANCE_M = 30
MAX_PLAUSIBLE_DISTANCE_M = 10000


def _normalize(text):
    """Lowercase a name and drop whitespace and punctuation for comparison."""
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", str(text).lower())


def _is_positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def check_data_integrity(data):
    """Run integrity checks on the dataset.

    Checks performed:
        * station data: names present, unique, with line information;
        * line coverage: main lines and representative stations present;
        * connections: valid fields, known endpoints, no self-loops or
          duplicates, lines consistent with station line lists;
        * distance accuracy: positive integers within a plausible range;
        * reverse connections present for each listed connection.

    Returns:
        tuple: (errors, warnings), each a list of message strings.
    """
    errors = []
    warnings = []

    stations = data.get("stations", [])
    connections = data.get("connections", [])

    # ----- station data ------------------------------------------------
    names = []
    station_lines = {}
    for index, station in enumerate(stations):
        name = station.get("name") if isinstance(station, dict) else None
        if not isinstance(name, str) or not name.strip():
            errors.append(f"Station entry #{index} has no valid name")
            continue
        name = " ".join(name.split())
        names.append(name)
        lines = station.get("lines")
        if not isinstance(lines, list) or not lines:
            warnings.append(f"Station '{name}' has no line information")
            lines = []
        station_lines.setdefault(name, set()).update(str(x) for x in lines)

    duplicates = {name for name in names if names.count(name) > 1}
    for name in sorted(duplicates):
        errors.append(f"Duplicate station name: '{name}'")

    name_set = set(names)
    normalized_names = {_normalize(name) for name in name_set}

    # ----- line and station coverage -----------------------------------
    all_lines = set()
    for lines in station_lines.values():
        all_lines.update(lines)
    for conn in connections:
        if isinstance(conn, dict) and isinstance(conn.get("line"), str):
            all_lines.add(conn["line"].strip())
    normalized_lines = {_normalize(line) for line in all_lines}

    for required in REQUIRED_LINES:
        if _normalize(required) not in normalized_lines:
            warnings.append(f"Main line '{required}' is not covered by the dataset")

    for representative in REPRESENTATIVE_STATIONS:
        if _normalize(representative) not in normalized_names:
            warnings.append(
                f"Representative station '{representative}' is not in the dataset")

    # ----- connection integrity and distance accuracy -------------------
    seen_keys = set()
    directed = set()
    for index, conn in enumerate(connections):
        if not isinstance(conn, dict):
            errors.append(f"Connection #{index} is not an object")
            continue
        source = conn.get("source")
        dest = conn.get("dest")
        line = conn.get("line")
        distance = conn.get("distance")
        if not isinstance(source, str) or not isinstance(dest, str) \
                or not isinstance(line, str):
            errors.append(f"Connection #{index} has missing source, dest, or line")
            continue
        source = " ".join(source.split())
        dest = " ".join(dest.split())
        line = line.strip()
        label = f"'{source}' -> '{dest}' ({line})"

        if source not in name_set:
            errors.append(f"Connection {label} references unknown station '{source}'")
        if dest not in name_set:
            errors.append(f"Connection {label} references unknown station '{dest}'")
        if source == dest:
            errors.append(f"Connection {label} is a self-loop")

        if not _is_positive_int(distance):
            errors.append(f"Connection {label} has invalid distance {distance!r}")
        elif not (MIN_PLAUSIBLE_DISTANCE_M <= distance <= MAX_PLAUSIBLE_DISTANCE_M):
            warnings.append(f"Connection {label} distance {distance} m is outside "
                            f"the plausible range")

        key = (source, dest, line)
        if key in seen_keys:
            errors.append(f"Duplicate connection {label}")
        seen_keys.add(key)
        directed.add((source, dest))

        for endpoint in (source, dest):
            if endpoint in station_lines and line not in station_lines[endpoint]:
                warnings.append(f"Station '{endpoint}' does not list line '{line}'")

    for source, dest in sorted(directed):
        if (dest, source) not in directed:
            warnings.append(f"Connection '{source}' -> '{dest}' has no reverse direction")

    return errors, warnings


def add_line(data, line_name, station_names, distances):
    """Add a new line with a sequence of stations and inter-station distances.

    Connections are created in both directions. Missing stations are added.

    Args:
        data: Raw dataset dictionary (modified in place).
        line_name: Name of the new line.
        station_names: Ordered list of station names on the line.
        distances: Distances in meters between consecutive stations.

    Returns:
        int: Number of connections added.

    Raises:
        ValueError: On invalid input or if the line already exists.
    """
    line_name = " ".join(str(line_name).split())
    if not line_name:
        raise ValueError("line name must not be empty")
    existing_lines = {conn.get("line") for conn in data["connections"]}
    for station in data["stations"]:
        existing_lines.update(station.get("lines", []))
    if line_name in existing_lines:
        raise ValueError(f"line '{line_name}' already exists")
    stations = [" ".join(str(name).split()) for name in station_names]
    if len(stations) < 2:
        raise ValueError("a line needs at least two stations")
    if len(set(stations)) != len(stations):
        raise ValueError("station names on a line must be distinct")
    if len(distances) != len(stations) - 1:
        raise ValueError("distances must have one entry per consecutive station pair")
    for distance in distances:
        if not _is_positive_int(distance):
            raise ValueError(f"invalid distance {distance!r}; must be a positive integer")

    by_name = {station["name"]: station for station in data["stations"]}
    for name in stations:
        if name not in by_name:
            entry = {"name": name, "lines": [line_name]}
            data["stations"].append(entry)
            by_name[name] = entry
        elif line_name not in by_name[name]["lines"]:
            by_name[name]["lines"].append(line_name)

    added = 0
    for index, distance in enumerate(distances):
        first, second = stations[index], stations[index + 1]
        data["connections"].append({"source": first, "dest": second,
                                    "distance": distance, "line": line_name})
        data["connections"].append({"source": second, "dest": first,
                                    "distance": distance, "line": line_name})
        added += 2
    return added


def modify_station(data, old_name, new_name=None, lines=None):
    """Rename a station and/or replace its line list.

    Connections referencing the old name are updated to the new name.

    Returns:
        dict: The updated station entry.

    Raises:
        KeyError: If the station does not exist.
        ValueError: If the new name already belongs to another station.
    """
    old_name = " ".join(old_name.split())
    station = next((s for s in data["stations"] if s["name"] == old_name), None)
    if station is None:
        raise KeyError(f"station '{old_name}' does not exist")
    if new_name is not None:
        new_name = " ".join(new_name.split())
        if not new_name:
            raise ValueError("new station name must not be empty")
        if new_name != old_name and any(s["name"] == new_name for s in data["stations"]):
            raise ValueError(f"station '{new_name}' already exists")
        station["name"] = new_name
        for conn in data["connections"]:
            if conn["source"] == old_name:
                conn["source"] = new_name
            if conn["dest"] == old_name:
                conn["dest"] = new_name
    if lines is not None:
        station["lines"] = list(dict.fromkeys(str(line).strip() for line in lines))
    return station


def update_distance(data, source, dest, distance, line=None):
    """Update the distance of the connection(s) from source to dest.

    Args:
        data: Raw dataset dictionary (modified in place).
        source: Origin station name.
        dest: Destination station name.
        distance: New distance in meters (positive integer).
        line: Optional line filter.

    Returns:
        int: Number of connections updated.

    Raises:
        ValueError: If the distance is invalid.
        LookupError: If no matching connection exists.
    """
    if not _is_positive_int(distance):
        raise ValueError("distance must be a positive integer (meters)")
    updated = 0
    for conn in data["connections"]:
        if conn["source"] == source and conn["dest"] == dest \
                and (line is None or conn["line"] == line):
            conn["distance"] = distance
            updated += 1
    if updated == 0:
        raise LookupError(f"no connection from '{source}' to '{dest}'")
    return updated


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write the dataset to a JSON file atomically."""
    directory = os.path.dirname(os.path.abspath(path))
    handle, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    except OSError:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
