"""Beijing Subway fare calculation system.

Package layout:
    data_loader     - loads subway_data.json
    models          - Edge, Graph, and query/route data classes
    pathfinding     - MinPQ, PathfindingConfig, ShortestPath (Dijkstra)
    fare_calculator - Sum_money and estimated travel time
    network         - SubwayNetwork: station registry, name matching, data updates, integrity checks
    query_service   - QueryService: runs a query end to end
    reporting       - text / JSON report rendering
    cli             - command-line interface
"""

__all__ = [
    "data_loader",
    "models",
    "pathfinding",
    "fare_calculator",
    "network",
    "query_service",
    "reporting",
    "cli",
]
