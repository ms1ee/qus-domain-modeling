import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
BENCHMARK_DIR = os.path.join(ROOT_DIR, "benchmark")
OUTDIR_BASE = os.path.join(ROOT_DIR, "output")

## Models: name -> (provider, model id)
MODELS = {
    "Claude-Opus-5.5": ("anthropic", "claude-opus-5-5"),
    "Claude-Haiku-5.5": ("anthropic", "claude-haiku-5-5"),
}

## Claude Opus/Haiku 5.5: no temperature (400), adaptive thinking, effort default medium
EFFORT = "medium"
MAX_TOKENS = 64000

## Benchmarks: PRDBench task id -> info. PRD file: benchmark/<id>/<prd>_PRD.md
## interface: code touchpoints of the scored unit tests that the PRD does not define (code generation only)
BENCHMARKS = {
    "37": {
        "name": "Company Team Building Event Smart Lottery System",
        "interface": """lottery_system.models
  User(name, department)
  Prize(name, quantity, avoid_groups, associated_drawer)    # avoid_groups: list[str], associated_drawer: str | None

lottery_system.services.list_manager.ListManager()
  load_default_list() -> (list[User], list[str] errors)
  load_custom_list(path) -> (list[User], list[str] errors)
  _load_from_path(path) -> (list[User], list[str] errors)
  validate_users(users) -> (list[User] valid_users, list[User] duplicates)
  get_group_info(users) -> dict[department, count]
  A format error message contains "Format Error" and names the line as "Line N".

lottery_system.services.prize_manager.PrizeManager()        # starts with no prizes
  load_default_prizes() -> list[str] errors
  add_prize(name, quantity, avoid_groups=None, associated_drawer=None)
  get_prizes() -> list[Prize]
  reorder_prizes(order: list[int]) -> bool                  # order: 1-based current positions in the new order

lottery_system.services.lottery_manager.LotteryManager(users)
  _get_eligible_pool(prize) -> list[User]
  last_two_draw_results: list[bool]                         # per draw: whether a Cheng Ru group member won

lottery_system.services.result_manager
  Winner                                                    # attr: user
  ResultManager()
    add_winner(user, prize)
    get_winners_by_prize(prizes) -> dict[prize name, list[Winner]]
    export_to_csv(prizes) -> (bool success, str message)    # success message contains "successfully exported"
""",
    },
    "44": {
        "name": "Beijing Subway Fare Calculation System",
        "interface": """Provided data file: src/subway_data.json (already present, do not write it)
  {"stations": [{"name": str, "lines": [str]}],
   "connections": [{"source": str, "dest": str, "distance": int (meters), "line": str}]}

Top-level modules under src/:
data_loader
  DATA_FILE_PATH                                  # path of src/subway_data.json, valid from any working directory
  load_subway_data(path) -> dict                  # the JSON content of the file
models
  Edge(source, dest, distance, line)              # source/dest: station numbers; attrs: weight (= distance), line
  Graph()
    set_station_lines(station_name, lines)
    add_edge(edge)
    station_lines: dict[station name, list[str]]
pathfinding
  PathfindingConfig()                             # attrs: mode, max_transfers, preferred_lines (list[str])
  ShortestPath(graph, source, config=None)        # source: station number
    dist_to: dict[station number, distance]
    path_with_edges(target) -> (list[station number], list[Edge])
    get_transfer_count(target) -> int
fare_calculator
  Sum_money(distance) -> int                      # distance in meters, fare in yuan
  calculate_estimated_time(distance, transfer_count) -> float   # distance in meters, time in minutes
""",
    },
    "29": {
        "name": "Food Delivery Order Dispatch System",
        "interface": """Top-level modules under src/:
globalvar
  _init()                                         # reset the global store
  set_value(key, value), get_value(key)           # key "riders": list[Rider]
system
  init_system()                                   # system startup: reset global state
rider
  Rider(rider_id)                                 # attrs: rider_id, x, y, speed, state, orders (list[Order]), log (list[dict])
    move()                                        # advance one tick; state transitions are applied here
    log entries: dict with keys "event" and "order_id"
      events: "spawn", "accepted_order", "arrived_at_merchant", "delivered_to_customer"
order_model
  Order(res_pos, cus_pos)                         # (x, y) tuples; attrs: id, status ("completed" after delivery)
    assign_to(rider_id)
order
  find_best_rider_for_order(order) -> Rider       # among the riders in globalvar "riders"
""",
    },
}
