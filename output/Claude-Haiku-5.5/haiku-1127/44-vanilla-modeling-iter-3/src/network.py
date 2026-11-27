"""Construction of the subway graph from the raw dataset."""

from typing import Any, Dict

from models import Edge, Graph


def build_graph(data: Dict[str, Any]) -> Graph:
    """Build a weighted undirected ``Graph`` from the subway dataset.

    Station numbers are assigned here (by position in the ``stations`` list);
    the ``Graph`` class itself does not assign numbers.

    Args:
        data: Dictionary with ``stations`` and ``connections`` lists.

    Returns:
        A populated ``Graph`` instance.

    Raises:
        ValueError: If the dataset references unknown stations or is malformed.
    """
    graph = Graph()
    for number, entry in enumerate(data.get("stations", [])):
        name = entry.get("name")
        graph.register_station(name, number)
        graph.set_station_lines(name, entry.get("lines", []))

    for index, conn in enumerate(data.get("connections", [])):
        try:
            source = graph.number_of(conn["source"])
            dest = graph.number_of(conn["dest"])
            distance = float(conn["distance"])
            line = conn["line"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Malformed connection #{index}: {exc}") from exc
        graph.add_edge(Edge(source, dest, distance, line))
    return graph
