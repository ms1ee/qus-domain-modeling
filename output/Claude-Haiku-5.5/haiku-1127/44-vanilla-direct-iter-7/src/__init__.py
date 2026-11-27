"""Beijing Subway fare calculation system.

Package layout:
    data_loader        - loads subway_data.json
    models             - Edge and Graph data structures
    min_pq             - heap-based priority queue (MinPQ)
    pathfinding        - PathfindingConfig and ShortestPath (Dijkstra)
    fare_calculator    - Sum_money and estimated travel time
    subway_network     - SubwayNetwork: builds the graph and manages network data
    query_service      - QueryService: combines path search and fare into a PathResult
    report             - console text, JSON, and summary output
    cli                - command-line interface (main entry point)
"""
