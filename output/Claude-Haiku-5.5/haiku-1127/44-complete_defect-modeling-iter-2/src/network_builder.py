"""
Builds a ``Graph`` from the raw subway dataset.

Station numbers are assigned here (the caller), as required by the
``Graph`` model. Stations referenced only by connections are registered
automatically, and the lines of every connection are added to the lines
served by both of its endpoints.
"""

from models import Edge, Graph


def build_graph(data):
    """
    Construct the weighted undirected subway graph from the dataset.

    Args:
        data: dict with ``stations`` (list of {name, lines}) and
              ``connections`` (list of {source, dest, distance, line}).

    Returns:
        Graph: The populated graph.

    Raises:
        KeyError / TypeError / ValueError: If the dataset is malformed.
    """
    station_lines = {}
    order = []

    # 1. Collect stations and their lines from the station list.
    for entry in data.get("stations", []):
        name = str(entry["name"]).strip()
        if not name:
            raise ValueError("station name cannot be empty")
        if name not in station_lines:
            station_lines[name] = []
            order.append(name)
        for line in entry.get("lines", []):
            if line not in station_lines[name]:
                station_lines[name].append(line)

    connections = data.get("connections", [])

    # 2. Make sure every connection endpoint is known and serves the line.
    for conn in connections:
        for endpoint in (str(conn["source"]).strip(), str(conn["dest"]).strip()):
            if endpoint not in station_lines:
                station_lines[endpoint] = []
                order.append(endpoint)
            if conn["line"] not in station_lines[endpoint]:
                station_lines[endpoint].append(conn["line"])

    # 3. Build the graph with caller-assigned numbers (0..n-1).
    graph = Graph()
    numbers = {}
    for index, name in enumerate(order):
        graph.add_station(name, index)
        numbers[name] = index
        graph.set_station_lines(name, station_lines[name])

    # 4. Add the connections as undirected weighted edges.
    for conn in connections:
        source = numbers[str(conn["source"]).strip()]
        dest = numbers[str(conn["dest"]).strip()]
        distance = conn["distance"]
        if not isinstance(distance, (int, float)) or isinstance(distance, bool):
            raise TypeError(f"distance of connection {conn!r} must be numeric")
        graph.add_edge(Edge(source, dest, distance, conn["line"]))

    return graph
