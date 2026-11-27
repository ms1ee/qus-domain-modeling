"""Beijing Subway fare calculation system.

Package layout:
    data_loader     - reads and writes the subway_data.json dataset
    models          - Edge, Graph, Station, Line, Transfer
    network         - builds and maintains the weighted subway graph
    pathfinding     - MinPQ, PathfindingConfig, ShortestPath (Dijkstra)
    fare_calculator - distance-based fare and travel time estimation
    report          - trip summaries and text/JSON report rendering
    integrity       - data integrity checks (--check_data)
    cli             - command-line interface and interactive query loop
"""
