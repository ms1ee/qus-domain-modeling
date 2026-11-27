from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


def show_groups(lm, users):
    for g, c in lm.get_group_info(users).items():
        print(f"  {g}: {c}")


def load_list(lm):
    c = input("1) default list  2) custom txt file: ").strip()
    if c == "2":
        path = input("Path: ").strip()
        users, errors = lm.load_custom_list(path)
    else:
        users, errors = lm.load_default_list()
    for e in errors:
        print(e)
    if errors and c == "2":
        a = input("Errors found. (r)emove invalid lines and continue / (t)erminate upload: ").strip().lower()
        if a != "r":
            print("Upload terminated.")
            return None
    valid, dups = lm.validate_users(users)
    for d in dups:
        print(f"Duplicate name: {d.name} ({d.department}) removed")
    print(f"Loaded {len(valid)} valid participants.")
    show_groups(lm, valid)
    return valid


def run_lottery(users, prizes, results):
    engine = LotteryManager(users)
    for idx, prize in enumerate(prizes, 1):
        print(f"\n=== Round {idx}: {prize.name} x{prize.quantity} ===")
        print("Rules:", engine.rule_description(prize))
        won = []
        terminated = False
        for n in range(1, prize.quantity + 1):
            while True:
                cmd = input("Enter to draw (pause / continue / terminate): ").strip().lower()
                if cmd == "pause":
                    while input("Paused. Type 'continue' to resume: ").strip().lower() != "continue":
                        pass
                    continue
                if cmd == "terminate":
                    terminated = True
                break
            if terminated:
                print("Round terminated, skipping.")
                break
            print(f"Currently drawing the {n}th winner...")
            u = engine.draw_one(prize)
            if u is None:
                print("No eligible participants left.")
                break
            results.add_winner(u, prize)
            won.append(u)
            print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
        engine.finish_round(prize, won)
        print(f"Round {idx} results:")
        for i, u in enumerate(won, 1):
            print(f"  {i}. {u.name} ({u.department})")
    print("\n=== Final winner list ===")
    for pname, ws in results.get_winners_by_prize(prizes).items():
        for w in ws:
            print(f"{w.user.name}, {w.user.department}, {pname}")


def main():
    lm = ListManager()
    pm = PrizeManager()
    pm.load_default_prizes()
    users = lm.load_default_list()[0]
    results = ResultManager()
    while True:
        print("\n1 Load list  2 View groups  3 List prizes  4 Add prize  5 Set avoid groups")
        print("6 Reorder prizes  7 Start lottery  8 Export  0 Exit")
        c = input("> ").strip()
        if c == "1":
            r = load_list(lm)
            if r is not None:
                users = r
        elif c == "2":
            show_groups(lm, users)
        elif c == "3":
            for i, p in enumerate(pm.get_prizes(), 1):
                print(f"{i}. {p.name} x{p.quantity} avoid={p.avoid_groups} drawer={p.associated_drawer}")
        elif c == "4":
            try:
                name = input("Name: ").strip()
                q = int(input("Quantity: "))
                d = input("Drawer (optional): ").strip() or None
                av = [x.strip() for x in input("Avoid groups (comma separated): ").split(",") if x.strip()]
                pm.add_prize(name, q, av, d)
            except ValueError as e:
                print("Invalid input:", e)
        elif c == "5":
            try:
                i = int(input("Prize number: "))
                av = [x.strip() for x in input("Avoid groups (comma separated): ").split(",") if x.strip()]
                pm.get_prizes()[i - 1].avoid_groups = av
            except (ValueError, IndexError):
                print("Invalid input.")
        elif c == "6":
            order = input("New order (e.g. 3 1 2): ").replace(",", " ").split()
            print("Reordered." if pm.reorder_prizes(order) else "Invalid order.")
        elif c == "7":
            results = ResultManager()
            run_lottery(users, pm.get_prizes(), results)
        elif c == "8":
            print(results.export_to_csv(pm.get_prizes())[1])
        elif c == "0":
            break


if __name__ == "__main__":
    main()
