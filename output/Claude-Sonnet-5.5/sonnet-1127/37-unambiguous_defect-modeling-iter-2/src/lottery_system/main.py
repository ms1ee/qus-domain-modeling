from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    choice = input("Load list: 1) default  2) custom txt file: ").strip()
    if choice == "2":
        users, errors = lm._load_from_path(input("Path: ").strip())
    else:
        users, errors = lm.load_default_list()
    for e in errors:
        print(e)
    if errors:
        a = input("Errors found. (r)emove invalid and continue / (t)erminate: ").strip().lower()
        if a != "r":
            return []
    valid, dups = lm.validate_users(users)
    for d in dups:
        print(f"Duplicate name removed: {d.name} ({d.department})")
    return valid


def configure_prizes(pm):
    if input("Load preset prizes? (y/n): ").strip().lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").strip().lower() == "y":
        name = input("Name: ").strip()
        try:
            q = int(input("Quantity: "))
        except ValueError:
            print("Invalid quantity")
            continue
        avoid = [g.strip() for g in input("Avoid groups (comma separated): ").split(",") if g.strip()]
        drawer = input("Associated drawer: ").strip() or None
        try:
            pm.add_prize(name, q, avoid, drawer)
        except ValueError as e:
            print(e)
    prizes = pm.get_prizes()
    for i, p in enumerate(prizes, 1):
        print(f"{i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
    s = input("New order (space separated numbers, blank to keep): ").split()
    if s:
        try:
            if not pm.reorder_prizes([int(x) for x in s]):
                print("Invalid order, keeping default")
        except ValueError:
            print("Invalid order, keeping default")


def run():
    lm = ListManager()
    users = load_users(lm)
    if not users:
        print("No valid participants.")
        return
    for g, c in lm.get_group_info(users).items():
        print(f"Group {g}: {c} people")
    pm = PrizeManager()
    configure_prizes(pm)
    prizes = pm.get_prizes()
    engine = LotteryManager(users)
    rm = ResultManager()
    for idx, prize in enumerate(prizes, 1):
        print(f"\n=== Round {idx}: {prize.name}, quantity {prize.quantity} ===")
        print("Rules:", engine.describe_rules(prize))
        round_winners = []
        n = 0
        while n < prize.quantity:
            cmd = input("Enter to draw (pause / continue / terminate): ").strip().lower()
            if cmd == "terminate":
                print("Round terminated.")
                break
            if cmd == "pause":
                while input("Paused. Type 'continue': ").strip().lower() != "continue":
                    pass
                continue
            print(f"Currently drawing the {n + 1}th winner")
            u = engine.draw_one(prize)
            if u is None:
                print("No eligible participants left.")
                break
            n += 1
            rm.add_winner(u, prize)
            round_winners.append(u)
            print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
        engine.record_round_result(round_winners)
        print("Round results:", ", ".join(u.name for u in round_winners) or "none")
    print("\n=== Final winners ===")
    for pname, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {pname}")
    if input("Export results? (y/n): ").strip().lower() == "y":
        print(rm.export_to_csv(prizes)[1])


if __name__ == "__main__":
    run()
