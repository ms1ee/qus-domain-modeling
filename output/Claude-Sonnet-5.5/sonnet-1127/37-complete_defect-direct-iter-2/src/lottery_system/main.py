from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    while True:
        c = input("1) Default list  2) Custom txt list: ").strip()
        if c == "1":
            users, errs = lm.load_default_list()
        elif c == "2":
            users, errs = lm.load_custom_list(input("Path: ").strip())
        else:
            continue
        for e in errs:
            print(e)
        if errs and input("Errors found. Remove invalid data and continue? (y/n): ").lower() != "y":
            if c == "2":
                print("Upload terminated.")
                continue
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate name removed: {d.name}")
        if valid:
            return valid
        print("No valid users.")


def setup_prizes(pm):
    if input("Load default prizes? (y/n): ").lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").lower() == "y":
        name = input("Prize name: ").strip()
        q = input("Quantity: ").strip()
        avoid = [g.strip() for g in input("Avoid groups (comma separated, optional): ").split(",") if g.strip()]
        drawer = input("Associated drawer (optional): ").strip() or None
        try:
            pm.add_prize(name, q, avoid, drawer)
        except ValueError as e:
            print(e)
    prizes = pm.get_prizes()
    for i, p in enumerate(prizes, 1):
        print(f"{i}. {p.name} x{p.quantity}")
    s = input("New order (e.g. 2 1 3), blank to keep: ").split()
    if s:
        try:
            if not pm.reorder_prizes([int(x) for x in s]):
                print("Invalid order, keeping default.")
        except ValueError:
            print("Invalid order, keeping default.")


def run_round(lot, res, prize):
    print(f"\n=== {prize.name} | quantity {prize.quantity} | drawer {prize.associated_drawer or '-'} "
          f"| avoid {', '.join(prize.avoid_groups) or 'none'} ===")
    won = []
    i = 1
    while i <= prize.quantity:
        cmd = input("Enter to draw (pause/terminate): ").strip().lower()
        if cmd == "terminate":
            print("Round terminated.")
            break
        if cmd == "pause":
            while input("Paused. Type 'continue': ").strip().lower() != "continue":
                pass
            continue
        print(f"Currently drawing the {i}th winner...")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible candidates left.")
            break
        res.add_winner(u, prize)
        won.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
        i += 1
    lot.finish_round(prize, won)


def main():
    lm = ListManager()
    users = load_users(lm)
    for g, n in lm.get_group_info(users).items():
        print(f"{g}: {n}")
    pm = PrizeManager()
    setup_prizes(pm)
    prizes = pm.get_prizes()
    lot = LotteryManager(users)
    res = ResultManager()
    for p in prizes:
        run_round(lot, res, p)
    print("\n=== Complete winner list ===")
    for name, ws in res.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name},{w.user.department},{name}")
    print(res.export_to_csv(prizes)[1])


if __name__ == "__main__":
    main()
