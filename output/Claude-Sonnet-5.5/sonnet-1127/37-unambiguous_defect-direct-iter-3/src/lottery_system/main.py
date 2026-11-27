from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    while True:
        c = input("1) default list  2) custom txt list: ").strip()
        if c == "1":
            users, errors = lm.load_default_list()
        elif c == "2":
            users, errors = lm.load_custom_list(input("Path: ").strip())
        else:
            continue
        for e in errors:
            print("Warning:", e)
        if errors and input("Errors found. Remove invalid data and continue? (y/n): ").lower() != "y":
            if c == "2":
                print("Upload terminated.")
                continue
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate removed: {d.name} ({d.department})")
        if valid:
            return valid
        print("No valid users.")


def configure_prizes(pm, groups):
    if input("Load preset prizes? (y/n): ").lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").lower() == "y":
        name = input("Name: ").strip()
        qty = input("Quantity: ").strip()
        avoid = [g.strip() for g in input(
            f"Avoid groups (comma separated, from {list(groups)}): ").split(",") if g.strip()]
        drawer = input("Associated drawer (blank for none): ").strip() or None
        try:
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print("Error:", e)
    for p in pm.get_prizes():
        if p.avoid_groups == [] and p.name.startswith("Third") and not p.associated_drawer:
            pass
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
    o = input("Enter new order as numbers (blank to keep): ").split()
    if o and not pm.reorder_prizes(o):
        print("Invalid order, keeping original.")


def run_round(lot, res, prize):
    print(f"\n=== {prize.name} | quantity {prize.quantity} | avoid {prize.avoid_groups or 'none'}"
          f" | drawer {prize.associated_drawer or 'none'} ===")
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
        print(f"Currently drawing the {n + 1}th winner...")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible participants left.")
            break
        res.add_winner(u, prize)
        got.append(u)
        n += 1
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
    lot.finish_prize(prize, got)
    print("Round results:")
    for i, u in enumerate(got, 1):
        print(f"  {i}. {u.name} ({u.department})")


def main():
    lm = ListManager()
    users = load_users(lm)
    for d, c in lm.get_group_info(users).items():
        print(f"  {d}: {c}")
    pm = PrizeManager()
    configure_prizes(pm, lm.get_group_info(users))
    lot = LotteryManager(users)
    res = ResultManager()
    prizes = pm.get_prizes()
    for p in prizes:
        run_round(lot, res, p)
    ordered = list(reversed(prizes))
    print("\n=== Final winners ===")
    for name, ws in res.get_winners_by_prize(ordered).items():
        for w in ws:
            print(f"{name}: {w.user.name} ({w.user.department})")
    ok, msg = res.export_to_csv(ordered)
    print(msg)


if __name__ == "__main__":
    main()
