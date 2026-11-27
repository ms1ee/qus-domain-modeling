from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def _rank(p):
    n = p.name.lower()
    for i, k in enumerate(("first", "second", "third")):
        if k in n:
            return i
    return 99


def load_users(lm):
    choice = input("Load list: 1) default  2) custom txt [1]: ").strip()
    if choice == "2":
        path = input("Path: ").strip()
        users, errors = lm.load_custom_list(path)
    else:
        users, errors = lm.load_default_list()
    for e in errors:
        print("Warning:", e)
    if errors and choice == "2":
        if input("Errors found. Continue with valid data? (y/n): ").strip().lower() != "y":
            return None
    users, dups = lm.validate_users(users)
    for d in dups:
        print(f"Duplicate removed: {d.name} ({d.department})")
    print("Groups:")
    for g, c in lm.get_group_info(users).items():
        print(f"  {g}: {c}")
    return users


def configure_prizes(pm, groups):
    if input("Load default prizes? (y/n) [y]: ").strip().lower() != "n":
        for e in pm.load_default_prizes():
            print("Warning:", e)
    while input("Add custom prize? (y/n) [n]: ").strip().lower() == "y":
        name = input("Name: ")
        qty = input("Quantity: ")
        avoid = [a.strip() for a in input("Avoid groups (comma separated): ").split(",") if a.strip()]
        drawer = input("Associated drawer: ").strip() or None
        try:
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print("Error:", e)
    prizes = pm.get_prizes()
    for i, p in enumerate(prizes, 1):
        print(f"{i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
    s = input("Enter new order as numbers (blank to keep): ").strip()
    if s:
        try:
            ok = pm.reorder_prizes([int(x) for x in s.replace(",", " ").split()])
        except ValueError:
            ok = False
        print("Reordered." if ok else "Invalid order, keeping original.")


def run_round(prize, lot, res):
    print(f"\n=== {prize.name} | quantity {prize.quantity} ===")
    print(f"Rules: avoid groups={prize.avoid_groups or 'none'}, drawer={prize.associated_drawer or 'n/a'}")
    won = []
    while len(won) < prize.quantity:
        cmd = input("Enter to draw (pause / terminate): ").strip().lower()
        if cmd == "terminate":
            print("Round terminated.")
            break
        if cmd == "pause":
            while input("Paused. Type 'continue': ").strip().lower() != "continue":
                pass
            continue
        print(f"Currently drawing the {len(won) + 1}th winner...")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible candidates left.")
            break
        res.add_winner(u, prize)
        won.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
    lot.finish_round(prize, won)
    print("Round results:")
    for i, u in enumerate(won, 1):
        print(f"  {i}. {u.name} ({u.department})")


def main():
    lm = ListManager()
    users = load_users(lm)
    if not users:
        print("No users loaded.")
        return
    pm = PrizeManager()
    configure_prizes(pm, lm.get_group_info(users))
    prizes = pm.get_prizes()
    lot, res = LotteryManager(users), ResultManager()
    for p in prizes:
        run_round(p, lot, res)
    print("\n=== Final winners ===")
    ordered = sorted(prizes, key=_rank)
    for name, ws in res.get_winners_by_prize(ordered).items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {name}")
    ok, msg = res.export_to_csv(ordered)
    print(msg)


if __name__ == "__main__":
    main()
