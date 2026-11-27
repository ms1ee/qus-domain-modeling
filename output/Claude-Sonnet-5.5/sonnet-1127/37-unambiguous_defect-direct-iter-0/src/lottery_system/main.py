from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def load_users(lm):
    while True:
        c = input("1) default list  2) custom txt list: ").strip()
        if c == "1":
            users, errs = lm.load_default_list()
        elif c == "2":
            users, errs = lm.load_custom_list(input("Path: ").strip())
        else:
            continue
        for e in errs:
            print("  !", e)
        if errs and input("Errors found. Remove invalid data and continue? (y/n): ").lower() != "y":
            if c == "2":
                print("Upload terminated.")
                continue
        valid, dups = lm.validate_users(users)
        for d in dups:
            print(f"  ! Duplicate removed: {d.name}")
        if valid:
            return valid
        print("No valid users.")


def configure_prizes(pm, groups):
    if input("Load default prizes? (y/n): ").lower() == "y":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").lower() == "y":
        try:
            name = input("Name: ").strip()
            qty = int(input("Quantity: "))
            avoid = [g.strip() for g in input("Avoid groups (comma separated): ").split(",") if g.strip()]
            drawer = input("Associated drawer: ").strip() or None
            pm.add_prize(name, qty, avoid, drawer)
        except ValueError as e:
            print("Invalid:", e)
    prizes = pm.get_prizes()
    for i, p in enumerate(prizes, 1):
        print(f"{i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
    s = input("New order (e.g. 2 1 3) or Enter to keep: ").split()
    if s:
        try:
            if not pm.reorder_prizes([int(x) for x in s]):
                print("Invalid order, kept original.")
        except ValueError:
            print("Invalid order, kept original.")


def run_round(lot, prize, rm):
    print(f"\n=== {prize.name} | quantity {prize.quantity} | avoid {prize.avoid_groups} "
          f"| drawer {prize.associated_drawer} ===")
    won = []
    paused = False
    while len(won) < prize.quantity:
        cmd = input(f"Enter to draw #{len(won) + 1} (pause/continue/terminate): ").strip().lower()
        if cmd == "pause":
            paused = True
            print("Paused. Type 'continue' to resume.")
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
        print(f"Currently drawing winner #{len(won) + 1}...")
        u = lot.draw_one(prize)
        if u is None:
            print("No eligible candidates left.")
            break
        won.append(u)
        rm.add_winner(u, prize)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
    lot.finish_round(prize, won)


def main():
    lm = ListManager()
    users = load_users(lm)
    for g, n in lm.get_group_info(users).items():
        print(f"  {g}: {n}")
    pm = PrizeManager()
    configure_prizes(pm, None)
    lot = LotteryManager(users)
    rm = ResultManager()
    prizes = pm.get_prizes()
    for p in prizes:
        run_round(lot, p, rm)
    print("\n=== Final Results ===")
    for name, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{name}: {w.user.name} ({w.user.department})")
    ok, msg = rm.export_to_csv(prizes)
    print(msg)


if __name__ == "__main__":
    main()
