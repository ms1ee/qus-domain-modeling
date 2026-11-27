"""Command-line interface for the lottery system."""

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


class LotteryCLI:
    def __init__(self, input_func=input, output_func=print):
        self.input = input_func
        self.out = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery = None
        self.status = "idle"

    def ask(self, prompt):
        try:
            return self.input(prompt).strip()
        except EOFError:
            return "0"

    # ---------- list ----------
    def _set_users(self, users):
        self.users = users
        self.lottery = LotteryManager(users, self.result_manager)

    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        valid, dups = self.list_manager.validate_users(users)
        self._set_users(valid)
        self.out(f"Default list loaded: {len(valid)} participants.")

    def load_custom(self):
        path = self.ask("Enter txt file path: ")
        users, errors = self.list_manager.load_custom_list(path)
        valid, dups = self.list_manager.validate_users(users)
        if not users and errors:
            for e in errors:
                self.out("  " + e)
            self.out("Upload failed.")
            return
        if errors or dups:
            self.out("Invalid data detected:")
            for e in errors:
                self.out("  " + e)
            for d in dups:
                self.out(f"  Duplicate Name: {d.name},{d.department}")
            choice = self.ask("Remove invalid data and continue (r) or terminate upload (t)? ").lower()
            if choice != "r":
                self.out("Upload terminated.")
                return
        self._set_users(valid)
        self.out(f"Custom list loaded: {len(valid)} valid participants.")

    def show_groups(self):
        if not self.users:
            self.out("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        self.out("Current valid groups:")
        for i, (g, c) in enumerate(info.items(), 1):
            self.out(f"  {i}. {g}: {c} people")

    # ---------- prizes ----------
    def load_preset_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            self.out("  " + e)
        self.out("Preset prize library loaded.")

    def add_custom_prize(self):
        name = self.ask("Prize name: ")
        qty = self.ask("Quantity: ")
        groups = list(self.list_manager.get_group_info(self.users).keys())
        avoid = []
        if groups:
            for i, g in enumerate(groups, 1):
                self.out(f"  {i}. {g}")
            sel = self.ask("Avoidance groups (numbers or names, comma-separated, empty for none): ")
        else:
            sel = self.ask("Avoidance groups (names, comma-separated, empty for none): ")
        for item in [s.strip() for s in sel.replace("，", ",").split(",") if s.strip()]:
            if item.isdigit() and 1 <= int(item) <= len(groups):
                g = groups[int(item) - 1]
            else:
                g = item
            if g not in avoid:
                avoid.append(g)
        drawer = self.ask("Associated lottery person (empty for none): ") or None
        try:
            p = self.prize_manager.add_prize(name, qty, avoid, drawer)
            self.out(f"Prize added: {p.name} x{p.quantity}")
        except ValueError as e:
            self.out(f"Error: {e}")

    def show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.out("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            self.out(f"  {i}. {p.name} x{p.quantity} | {p.rule_description()}")

    def reorder(self):
        self.show_prizes()
        if not self.prize_manager.get_prizes():
            return
        s = self.ask("Enter new order of serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in s.replace("，", ",").replace(" ", ",").split(",") if x]
        except ValueError:
            self.out("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            self.out("Prize order updated.")
            self.show_prizes()
        else:
            self.out("Invalid order; must be a permutation of all serial numbers.")

    # ---------- lottery ----------
    def _control(self):
        """Return True to draw, False to terminate round."""
        cmd = self.ask("[Enter]=draw | pause | terminate > ").lower()
        if cmd == "terminate":
            return False
        if cmd == "pause":
            self.status = "paused"
            self.out("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
            while True:
                c = self.ask("(paused) > ").lower()
                if c == "continue":
                    self.status = "running"
                    self.out("Lottery resumed.")
                    return True
                if c in ("terminate", "0"):
                    self.status = "running"
                    return False
        return True

    def run_lottery(self):
        if not self.users:
            self.out("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.out("Please configure prizes first.")
            return
        self.status = "running"
        for rnd, prize in enumerate(prizes, 1):
            remaining = self.lottery.remaining_quantity(prize)
            if remaining == 0:
                continue
            self.out(f"\n===== Round {rnd}: {prize.name} (quantity: {prize.quantity}) =====")
            self.out("Rules: " + self.lottery.describe_rules(prize))
            round_winners = []
            already = prize.quantity - remaining
            for i in range(remaining):
                if not self._control():
                    self.out("Current round terminated, skipping.")
                    break
                self.out(f"Currently drawing the {ordinal(already + i + 1)} winner...")
                user = self.lottery.draw_one(prize)
                if user is None:
                    self.out("No eligible participants left for this prize.")
                    break
                round_winners.append(user)
                self.out(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            self.lottery.finish_round(prize, round_winners)
            self.out(f"--- Round {rnd} results ---")
            if round_winners:
                for i, u in enumerate(round_winners, 1):
                    self.out(f"  {i}. {u.name} ({u.department})")
            else:
                self.out("  No winners in this round.")
        self.status = "finished"
        self.out("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self):
        data = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        self.out("===== Complete Winner List =====")
        if not self.result_manager.winners:
            self.out("No winners yet.")
            return
        for pname, ws in data.items():
            if not ws:
                continue
            self.out(f"[{pname}]")
            for w in ws:
                self.out(f"  {w.user.name} ({w.user.department}) - {w.time:%Y-%m-%d %H:%M:%S}")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        self.out(msg)

    # ---------- main loop ----------
    def run(self):
        actions = {
            "1": self.load_default, "2": self.load_custom, "3": self.show_groups,
            "4": self.load_preset_prizes, "5": self.add_custom_prize, "6": self.show_prizes,
            "7": self.reorder, "8": self.run_lottery, "9": self.show_summary, "10": self.export,
        }
        while True:
            self.out("\n==== Team Building Smart Lottery System ====")
            self.out("1. Load default list      2. Upload custom list    3. View groups")
            self.out("4. Load preset prizes     5. Add custom prize      6. View prizes")
            self.out("7. Reorder prizes         8. Start lottery         9. Show results")
            self.out("10. Export results        0. Exit")
            c = self.ask("Choose: ")
            if c == "0":
                self.out("Bye.")
                return
            act = actions.get(c)
            if act:
                act()
            else:
                self.out("Invalid choice.")


def main():
    LotteryCLI().run()


if __name__ == "__main__":
    main()
