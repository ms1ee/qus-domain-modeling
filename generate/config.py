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
}

PIPELINES = ["direct", "modeling"]
