from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    while True:
        c = input("1) default list  2) custom txt list: ").strip()
        if c == "2":
            users, errs = lm.load_custom_list(input("Path: ").strip())
        else:
            users, errs = lm.load_default_list()
        for e in errs:
            print(e)
        if errs:
            a = input("Errors found. (r)emove invalid and continue / (t)erminate: ").strip().lower()
            if a != "r":
                continue
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate removed: {d.name}")
        if valid:
            return valid
        print("No valid users.")


def setup_prizes(pm, groups):
    pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").strip().lower() == "y":
        try:
            name = input("Name: ")
            qty = int(input("Quantity: "))
            avoid = [g.strip() for g in input("Avoid groups (comma separated): ").split(",") if g.strip()]
            drawer = input("Associated drawer (blank for none): ").strip() or None
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print(f"Invalid: {e}")
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
    s = input("New order (e.g. 3 1 2) or blank: ").split()
    if s:
        try:
            if not pm.reorder_prizes([int(x) for x in s]):
                print("Invalid order, keeping default.")
        except ValueError:
            print("Invalid order, keeping default.")


def run():
    lm = ListManager()
    users = load_users(lm)
    info = lm.get_group_info(users)
    for g, n in info.items():
        print(f"{g}: {n}")
    pm = PrizeManager()
    setup_prizes(pm, info)
    lot = LotteryManager(users)
    rm = ResultManager()
    prizes = pm.get_prizes()
    for p in prizes:
        print(f"\n== {p.name} | quantity {p.quantity} | avoid {p.avoid_groups} | drawer {p.associated_drawer}")
        round_winners = []
        i = 0
        while i < p.quantity:
            cmd = input("Enter to draw (pause/continue/terminate): ").strip().lower()
            if cmd == "terminate":
                print("Round terminated.")
                break
            if cmd == "pause":
                while input("Paused. Type 'continue': ").strip().lower() != "continue":
                    pass
                continue
            print(f"Currently drawing the {i + 1}th winner")
            u = lot.draw_one(p)
            if u is None:
                print("No eligible candidates left.")
                break
            rm.add_winner(u, p)
            round_winners.append(u)
            print(f"Congratulations {u.name} ({u.department}) for winning {p.name}")
            i += 1
        lot.finish_round(p, round_winners)
    print("\n=== Final Results ===")
    for name, ws in rm.get_winners_by_prize(list(reversed(prizes))).items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {name}")
    print(rm.export_to_csv(prizes)[1])


if __name__ == "__main__":
    run()
