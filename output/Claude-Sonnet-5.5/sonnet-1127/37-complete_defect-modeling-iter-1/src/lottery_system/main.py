from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    print("1. Default list  2. Custom txt list")
    if input("Choose: ").strip() == "2":
        users, errors = lm.load_custom_list(input("Path: ").strip())
        for e in errors:
            print("  !", e)
        if errors and input("Errors found. Remove invalid data and continue? (y/n): ").lower() != "y":
            return []
    else:
        users, _ = lm.load_default_list()
    users, dups = lm.validate_users(users)
    for d in dups:
        print(f"  ! Duplicate removed: {d.name}")
    print("Groups:")
    for g, c in lm.get_group_info(users).items():
        print(f"  {g}: {c}")
    return users


def config_prizes(pm, groups):
    if input("Load preset prizes? (y/n): ").lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").lower() == "y":
        try:
            name = input("Name: ").strip()
            q = int(input("Quantity: "))
            drawer = input("Lottery person (blank for none): ").strip() or None
            av = [a.strip() for a in input(f"Avoid groups, comma-separated {groups}: ").split(",") if a.strip()]
            pm.add_prize(name, q, av, drawer)
        except ValueError as e:
            print("Invalid:", e)
    ps = pm.get_prizes()
    for i, p in enumerate(ps, 1):
        print(f"{i}. {p.name} x{p.quantity} drawer={p.associated_drawer} avoid={p.avoid_groups}")
    o = input("New order (e.g. 2,1,3) or Enter to keep: ").strip()
    if o:
        ok = pm.reorder_prizes([x for x in o.replace(" ", "").split(",") if x])
        print("Reordered." if ok else "Invalid order, kept original.")


def run_round(lot, rm, prize):
    print(f"\n=== {prize.name} | quantity {prize.quantity} | drawer {prize.associated_drawer} ===")
    print("Rules:", lot.describe_rules(prize))
    won = []
    i = 1
    while i <= prize.quantity:
        cmd = input("[Enter]=draw, pause, terminate: ").strip().lower()
        if cmd == "pause":
            while input("Paused. Type 'continue': ").strip().lower() != "continue":
                pass
            continue
        if cmd == "terminate":
            print("Round terminated.")
            break
        print(f"Currently drawing the {i}th winner...")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible participants remain.")
            break
        rm.add_winner(u, prize)
        won.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
        i += 1
    lot.finish_round(prize, won)
    print("Round results:", [w.name for w in won])


def main():
    lm = ListManager()
    users = load_users(lm)
    if not users:
        print("No participants.")
        return
    pm = PrizeManager()
    config_prizes(pm, sorted(lm.get_group_info(users)))
    prizes = pm.get_prizes()
    lot, rm = LotteryManager(users), ResultManager()
    for p in prizes:
        run_round(lot, rm, p)
    print("\n=== All Winners ===")
    for name, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name},{w.user.department},{name}")
    if input("Export results? (y/n): ").lower() == "y":
        print(rm.export_to_csv(prizes)[1])


if __name__ == "__main__":
    main()
