import os
import queue
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


class Input:
    def __init__(self):
        self.q = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        while True:
            line = sys.stdin.readline()
            if not line:
                self.q.put(None)
                return
            self.q.put(line.strip())

    def ask(self, prompt=""):
        print(prompt, end="", flush=True)
        v = self.q.get()
        if v is None:
            raise EOFError
        return v

    def poll(self):
        try:
            v = self.q.get_nowait()
        except queue.Empty:
            return ""
        if v is None:
            raise EOFError
        return v.lower()


def load_list(inp, lm):
    c = inp.ask("1) default list  2) custom txt file: ")
    if c == "1":
        users, errs = lm.load_default_list()
    elif c == "2":
        users, errs = lm.load_custom_list(inp.ask("Path: "))
    else:
        print("Invalid choice.")
        return None
    if errs:
        print("Problems found:")
        for e in errs:
            print("  " + e)
        if inp.ask("Remove invalid data and continue? (y/n): ").lower() != "y":
            print("Upload terminated.")
            return None
    valid, dups = lm.validate_users(users)
    if dups:
        print("Duplicate names:")
        for d in dups:
            print(f"  {d.name} ({d.department})")
        if inp.ask("Remove duplicates and continue? (y/n): ").lower() != "y":
            print("Upload terminated.")
            return None
    print(f"Loaded {len(valid)} participants.")
    return valid


def show_groups(lm, users):
    for g, n in lm.get_group_info(users).items():
        print(f"  {g}: {n}")


def show_prizes(pm):
    for i, p in enumerate(pm.get_prizes(), 1):
        print(f"  {i}. {p.name} x{p.quantity} avoid={p.avoid_groups or '-'} drawer={p.associated_drawer or '-'}")


def prize_menu(inp, pm, users, lm):
    while True:
        print("\nPrizes: 1 load presets, 2 add custom, 3 reorder, 4 list, 0 back")
        c = inp.ask("> ")
        if c == "1":
            for e in pm.load_default_prizes():
                print(e)
        elif c == "2":
            name = inp.ask("Prize name: ")
            try:
                q = int(inp.ask("Quantity: "))
            except ValueError:
                print("Invalid quantity.")
                continue
            drawer = inp.ask("Lottery person (blank for none): ") or None
            if users:
                print("Groups:")
                show_groups(lm, users)
            av = inp.ask("Avoid groups (comma separated, blank none): ")
            avoid = [a.strip() for a in av.split(",") if a.strip()]
            try:
                pm.add_prize(name, q, avoid, drawer)
            except ValueError as e:
                print(e)
        elif c == "3":
            show_prizes(pm)
            raw = inp.ask("New order (e.g. 3 1 2): ")
            if not pm.reorder_prizes(raw.replace(",", " ").split()):
                print("Invalid order.")
        elif c == "4":
            show_prizes(pm)
        elif c == "0":
            return


def run_lottery(inp, users, pm, rm):
    lot = LotteryManager(users)
    prizes = pm.get_prizes()
    print("Commands during lottery: pause / continue / terminate")
    for rno, prize in enumerate(prizes, 1):
        print(f"\n=== Round {rno}: {prize.name} x{prize.quantity} ===")
        print("Rules: " + lot.rule_description(prize))
        winners = []
        for i in range(1, prize.quantity + 1):
            cmd = inp.poll()
            if cmd == "pause":
                print("Paused. Type 'continue' to resume or 'terminate' to skip round.")
                while cmd not in ("continue", "terminate"):
                    cmd = inp.ask("") .lower()
            if cmd == "terminate":
                print("Round terminated.")
                break
            print(f"Currently drawing the {i}th winner...")
            time.sleep(0.5)
            u = lot.draw_one(prize)
            if u is None:
                print("No eligible participants remain.")
                break
            winners.append(u)
            rm.add_winner(u, prize)
            print(f"Congratulations {u.name} ({u.department}) for winning {prize.name}")
        lot.finish_round(prize, winners)
        print(f"Round {rno} results:")
        for k, u in enumerate(winners, 1):
            print(f"  {k}. {u.name} ({u.department})")
    print("\n=== Final winners ===")
    show_results(rm, prizes)


def show_results(rm, prizes):
    for pname, ws in rm.get_winners_by_prize(prizes).items():
        print(pname)
        for w in ws:
            print(f"  {w.user.name} ({w.user.department})")


def main():
    inp = Input()
    lm = ListManager()
    pm = PrizeManager()
    rm = ResultManager()
    users = []
    try:
        while True:
            print("\n1 load list, 2 view groups, 3 prizes, 4 start lottery, 5 results/export, 0 exit")
            c = inp.ask("> ")
            if c == "1":
                r = load_list(inp, lm)
                if r is not None:
                    users = r
            elif c == "2":
                show_groups(lm, users) if users else print("No list loaded.")
            elif c == "3":
                prize_menu(inp, pm, users, lm)
            elif c == "4":
                if not users or not pm.get_prizes():
                    print("Load a list and configure prizes first.")
                else:
                    rm = ResultManager()
                    run_lottery(inp, users, pm, rm)
                    if inp.ask("Export results? (y/n): ").lower() == "y":
                        print(rm.export_to_csv(pm.get_prizes())[1])
            elif c == "5":
                show_results(rm, pm.get_prizes())
                if rm.winners and inp.ask("Export? (y/n): ").lower() == "y":
                    print(rm.export_to_csv(pm.get_prizes())[1])
            elif c == "0":
                break
    except EOFError:
        pass


if __name__ == "__main__":
    main()
