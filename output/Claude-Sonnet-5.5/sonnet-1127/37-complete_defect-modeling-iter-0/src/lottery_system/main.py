from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def setup_list(lm):
    while True:
        c = input("List: 1) default 2) custom txt: ").strip()
        if c == "2":
            users, errs = lm.load_custom_list(input("Path: ").strip())
            for e in errs:
                print(e)
            if errs and input("Terminate upload? (y/n): ").strip().lower() == "y":
                continue
        else:
            users, _ = lm.load_default_list()
        users, dups = lm.validate_users(users)
        for d in dups:
            print(f"Duplicate removed: {d.name}")
        if users:
            return users
        print("No valid users.")


def setup_prizes(pm):
    if input("Load default prizes? (y/n): ").strip().lower() != "n":
        pm.load_default_prizes()
    while input("Add custom prize? (y/n): ").strip().lower() == "y":
        try:
            name = input("Name: ").strip()
            q = int(input("Quantity: "))
            drawer = input("Drawer (blank for none): ").strip() or None
            avoid = [g.strip() for g in input("Avoid groups (comma sep): ").split(",") if g.strip()]
            pm.add_prize(name, q, avoid, drawer)
        except ValueError as e:
            print(f"Invalid input: {e}")
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"{i}. {p.name} x{p.quantity}")
    o = input("New order (e.g. 2,1,3) or blank: ").strip()
    if o:
        try:
            if not pm.reorder_prizes([int(x) for x in o.split(",")]):
                print("Invalid order; keeping original.")
        except ValueError:
            print("Invalid order; keeping original.")


def run_round(num, prize, mgr, rm):
    avoid = ", ".join(prize.avoid_groups) or "none"
    print(f"\n=== Round {num}: {prize.name} x{prize.quantity} | drawer: "
          f"{prize.associated_drawer or 'n/a'} | avoid: {avoid} ===")
    won = []
    i = 1
    while i <= prize.quantity:
        cmd = input("Enter to draw (pause/terminate): ").strip().lower()
        if cmd == "pause":
            while input("Paused. Type 'continue': ").strip().lower() != "continue":
                pass
            continue
        if cmd == "terminate":
            print("Round terminated.")
            break
        print(f"Currently drawing the {i}th winner...")
        u = mgr.draw(prize)
        if u is None:
            print("No eligible participants.")
            break
        rm.add_winner(u, prize)
        won.append(u)
        print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
        i += 1
    mgr.finish_round(prize, won)


def main():
    lm = ListManager()
    users = setup_list(lm)
    for d, c in lm.get_group_info(users).items():
        print(f"{d}: {c}")
    pm = PrizeManager()
    setup_prizes(pm)
    mgr = LotteryManager(users)
    rm = ResultManager()
    prizes = pm.get_prizes()
    for n, p in enumerate(prizes, 1):
        run_round(n, p, mgr, rm)
    print("\n=== All Winners ===")
    for p, ws in rm.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {p}")
    if input("Export results? (y/n): ").strip().lower() == "y":
        print(rm.export_to_csv(prizes)[1])


if __name__ == "__main__":
    main()
