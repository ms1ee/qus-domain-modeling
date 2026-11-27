"""Loading of the Beijing Subway dataset and construction of the network model."""

import json
import os

from models import Network

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_PATH = os.path.join(_THIS_DIR, "subway_data.json")


class DataError(Exception):
    """Raised when the subway data file cannot be loaded or has an invalid structure."""


def load_subway_data(path):
    """Read the subway JSON file and return its content as a dictionary."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataError(f"Subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataError(f"Subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataError(f"Cannot read subway data file: {exc}") from exc

    if not isinstance(data, dict):
        raise DataError("Subway data must be a JSON object")
    for key in ("stations", "connections"):
        if key not in data or not isinstance(data[key], list):
            raise DataError(f"Subway data is missing the '{key}' list")
    return data


def build_network(data):
    """Build a Network (graph plus name/number mappings) from loaded data.

    Problems in individual records (unknown stations, invalid distances) are
    recorded in ``network.load_warnings`` instead of aborting the load, and
    bad connections are skipped.
    """
    network = Network()

    for index, station in enumerate(data["stations"]):
        if not isinstance(station, dict) or not station.get("name"):
            raise DataError(f"Station entry #{index} has no name")
        lines = station.get("lines", [])
        if not isinstance(lines, list):
            raise DataError(f"Station '{station['name']}' has an invalid 'lines' field")
        network.add_station(station["name"], lines)

    seen = set()
    for index, conn in enumerate(data["connections"]):
        if not isinstance(conn, dict):
            network.load_warnings.append(f"Connection entry #{index} is malformed; skipped")
            continue
        source = conn.get("source")
        dest = conn.get("dest")
        distance = conn.get("distance")
        line = conn.get("line", "")

        if not source or not dest or source == dest:
            network.load_warnings.append(f"Connection entry #{index} has invalid endpoints; skipped")
            continue
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            network.load_warnings.append(
                f"Connection {source} - {dest} ({line}) has an invalid distance; skipped")
            continue

        for name in (source, dest):
            if not network.has_station(name):
                network.add_station(name, [line] if line else [])
                network.load_warnings.append(
                    f"Station '{name}' used by a connection is missing from the station list")

        # Connections are bidirectional: keep one edge per (station pair, line).
        key = (frozenset((source, dest)), line)
        if key in seen:
            continue
        seen.add(key)
        network.add_connection(source, dest, int(distance), line)

    return network
