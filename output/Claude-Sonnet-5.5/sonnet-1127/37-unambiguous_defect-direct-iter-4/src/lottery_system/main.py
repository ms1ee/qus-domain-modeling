from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    c = input("1) default list  2) custom txt file [1]: ").strip()
    if c == "2":
        users, errors = lm.load_custom_list(input("Path: ").strip())
    else:
        users, errors = lm.load_default_list()
    for e in errors:
        print("  !", e)
    if errors and input("Terminate upload? (y/N): ").strip().lower() == "y":
        return []
    valid, dups = lm.validate_users(users)
    for d in dups:
        print(f"  ! Duplicate removed: {d.name}")
    print("Groups:")
    for g, n in lm.get_group_info(valid).items():
        print(f"  {g}: {n}")
    return valid


def config_prizes(pm, users):
    if input("Load default prizes? (Y/n): ").strip().lower() != "n":
        pm.load_default_prizes()
    while input("Add custom prize? (y/N): ").strip().lower() == "y":
        name = input("Name: ").strip()
        try:
            q = int(input("Quantity: "))
            avoid = [g.strip() for g in input("Avoid groups (comma-separated): ").split(",") if g.strip()]
            drawer = input("Associated drawer: ").strip() or None
            pm.add_prize(name, q, avoid, drawer)
        except ValueError as e:
            print("  !", e)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity}")
    s = input("New order (e.g. 3 1 2), blank to keep: ").split()
    if s:
        try:
            if not pm.reorder_prizes([int(x) for x in s]):
                print("  ! Invalid order, kept original")
        except ValueError:
            print("  ! Invalid order, kept original")


def run_round(lot, prize, res):
    print(f"\n=== {prize.name} | quantity {prize.quantity} | avoid: "
          f"{', '.join(prize.avoid_groups) or 'none'} | drawer: {prize.associated_drawer or '-'}")
    got = []
    while len(got) < prize.quantity:
        cmd = input("[Enter]=draw, pause, continue, terminate: ").strip().lower()
        if cmd == "terminate":
            print("Round terminated.")
            break
        if cmd == "pause":
            while input("Paused. Type 'continue': ").strip().lower() != "continue":
                pass
            continue
        print(f"Currently drawing the {len(got) + 1}th winner...")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible candidates left.")
            break
        res.add_winner(u, prize)
        got.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
    lot.record_round_result(prize, got)


def main():
    lm = ListManager()
    users = load_users(lm)
    if not users:
        print("No users loaded.")
        return
    pm = PrizeManager()
    config_prizes(pm, users)
    lot = LotteryManager(users)
    res = ResultManager()
    for p in pm.get_prizes():
        run_round(lot, p, res)
    print("\n=== Final Results ===")
    for name, ws in res.get_winners_by_prize(pm.get_prizes()).items():
        for w in ws:
            print(f"{name}: {w.user.name} ({w.user.department})")
    print(res.export_to_csv(pm.get_prizes())[1])


if __name__ == "__main__":
    main()
