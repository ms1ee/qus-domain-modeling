from .services.list_manager import ListManager
from .services.prize_manager import PrizeManager
from .services.lottery_manager import LotteryManager
from .services.result_manager import ResultManager


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
            print(f"Duplicate name removed: {d.name} ({d.department})")
        if valid:
            return valid
        print("No valid users.")


def run_round(lottery, results, prize, idx_total):
    print(f"\n=== {prize.name} | quantity {prize.quantity} | drawer: {prize.associated_drawer} "
          f"| avoid: {', '.join(prize.avoid_groups) or 'none'} ===")
    got = []
    n = 0
    while n < prize.quantity:
        cmd = input("Enter to draw (pause / terminate): ").strip().lower()
        if cmd == "terminate":
            print("Round terminated.")
            break
        if cmd == "pause":
            while input("Paused. Type 'continue': ").strip().lower() != "continue":
                pass
            continue
        print(f"Currently drawing the {n + 1}th winner...")
        u = lottery.draw_one(prize)
        if u is None:
            print("No eligible candidates left.")
            break
        n += 1
        results.add_winner(u, prize)
        got.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
    lottery.record_round(prize, got)
    print("Round results:")
    for i, u in enumerate(got, 1):
        print(f" {i}. {u.name} ({u.department})")


def main():
    lm = ListManager()
    users = load_users(lm)
    for g, c in lm.get_group_info(users).items():
        print(f"{g}: {c}")
    pm = PrizeManager()
    if input("Load default prizes? (y/n): ").lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").lower() == "y":
        try:
            name = input("Name: ")
            qty = input("Quantity: ")
            avoid = [x.strip() for x in input("Avoid groups (comma separated): ").split(",") if x.strip()]
            drawer = input("Associated drawer: ").strip() or None
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print(e)
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity}")
    o = input("New order (space separated, Enter to keep): ").split()
    if o and not pm.reorder_prizes(o):
        print("Invalid order, keeping default.")
    lottery = LotteryManager(users)
    results = ResultManager()
    prizes = pm.get_prizes()
    for p in prizes:
        run_round(lottery, results, p, len(prizes))
    print("\n=== Final winners ===")
    for name, ws in results.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {name}")
    ok, msg = results.export_to_csv(prizes)
    print(msg)


if __name__ == "__main__":
    main()
