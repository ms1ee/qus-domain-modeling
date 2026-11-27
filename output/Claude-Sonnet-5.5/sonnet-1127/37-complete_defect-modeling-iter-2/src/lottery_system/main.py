from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    c = input("Load list: 1) default 2) custom txt [1]: ").strip()
    if c == "2":
        users, errors = lm.load_custom_list(input("Path: ").strip())
        for e in errors:
            print(e)
        if errors and input("Invalid data found. Remove invalid lines and continue? (y/n): ").lower() != "y":
            return []
    else:
        users, _ = lm.load_default_list()
    valid, dups = lm.validate_users(users)
    for d in dups:
        print(f"Duplicate name removed: {d.name}")
    return valid


def configure_prizes(pm, groups):
    if input("Load preset prizes? (y/n) [y]: ").strip().lower() != "n":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n) [n]: ").strip().lower() == "y":
        name = input("Name: ").strip()
        try:
            q = int(input("Quantity: "))
            av = [g.strip() for g in input("Avoid groups (comma separated): ").split(",") if g.strip()]
            dr = input("Drawer (optional): ").strip() or None
            pm.add_prize(name, q, av, dr)
        except ValueError as e:
            print("Invalid:", e)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity}")
    o = input("New order (space separated numbers, blank to keep): ").split()
    if o:
        try:
            if not pm.reorder_prizes([int(x) for x in o]):
                print("Invalid order, keeping default.")
        except ValueError:
            print("Invalid order, keeping default.")


def run_round(lot, res, prize, num):
    print(f"\n=== Round {num}: {prize.name} (x{prize.quantity}) ===")
    print("Rules:", lot.describe_rules(prize))
    won = []
    i = 0
    paused = False
    while i < prize.quantity:
        cmd = input("Enter to draw (pause/continue/terminate): ").strip().lower()
        if cmd == "pause":
            paused = True
            print("Paused.")
            continue
        if cmd == "continue":
            paused = False
            continue
        if cmd == "terminate":
            print("Round terminated.")
            break
        if paused:
            print("Paused. Type 'continue' to resume.")
            continue
        print(f"Currently drawing the {i + 1}th winner")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible participants left.")
            break
        res.add_winner(u, prize)
        won.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
        i += 1
    lot.finish_round(prize, won)


def main():
    lm = ListManager()
    users = load_users(lm)
    if not users:
        print("No participants.")
        return
    for g, c in lm.get_group_info(users).items():
        print(f"{g}: {c}")
    pm = PrizeManager()
    configure_prizes(pm, lm.get_group_info(users))
    lot = LotteryManager(users)
    res = ResultManager()
    for n, p in enumerate(pm.get_prizes(), 1):
        run_round(lot, res, p, n)
    print("\n=== Final Winners ===")
    for p in pm.get_prizes():
        for w in res.get_winners_by_prize(pm.get_prizes())[p.name]:
            print(f"{w.user.name}, {w.user.department}, {p.name}")
    if input("Export results? (y/n): ").strip().lower() == "y":
        print(res.export_to_csv(pm.get_prizes())[1])


if __name__ == "__main__":
    main()
