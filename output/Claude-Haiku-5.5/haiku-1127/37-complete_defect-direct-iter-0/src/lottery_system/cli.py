"""Command-line interface for the lottery process."""

from __future__ import annotations

from typing import Callable

from .models import LI_BIN, MA_JIAQI, Prize, normalize
from .services.list_manager import ListManager
from .services.lottery_manager import LotteryManager
from .services.prize_manager import PrizeManager
from .services.result_manager import ResultManager


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def describe_rule(prize: Prize) -> str:
    """Human-readable rule description for a prize round."""
    parts = ["previous winners are excluded"]
    drawer = prize.associated_drawer
    if drawer:
        parts.insert(0, f"lottery person: {drawer}")
    if drawer and normalize(drawer) == normalize(LI_BIN):
        parts.append("special rule: avoidance groups are not applied")
    else:
        if prize.avoid_groups:
            parts.append("avoid groups: " + ", ".join(prize.avoid_groups))
        if drawer and normalize(drawer) == normalize(MA_JIAQI):
            parts.append("Cheng Ru Group protection fallback may apply")
    return "; ".join(parts)


class LotteryCLI:
    """Interactive console application."""

    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        output_func: Callable[..., None] = print,
    ) -> None:
        self._input = input_func
        self._print = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery_completed = False

    # ----- io helpers -----
    def _ask(self, prompt: str) -> str:
        return self._input(prompt)

    def _say(self, message: str = "") -> None:
        self._print(message)

    def _confirm(self, prompt: str) -> bool:
        answer = self._ask(f"{prompt} (y/n): ").strip().lower()
        return answer in ("y", "yes")

    # ----- main loop -----
    def run(self) -> None:
        self._say("=== Company Team Building Smart Lottery System ===")
        while True:
            self._show_menu()
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                self._load_default_list()
            elif choice == "2":
                self._load_custom_list()
            elif choice == "3":
                self._view_groups()
            elif choice == "4":
                self._load_default_prizes()
            elif choice == "5":
                self._add_prize()
            elif choice == "6":
                self._view_prizes()
            elif choice == "7":
                self._reorder_prizes()
            elif choice == "8":
                self._start_lottery()
            elif choice == "9":
                self._view_results()
            elif choice == "10":
                self._export_results()
            elif choice == "0":
                self._say("Goodbye!")
                return
            else:
                self._say("Invalid option, please try again.")

    def _show_menu(self) -> None:
        self._say("")
        self._say("---------------- Main Menu ----------------")
        self._say("1. Load built-in default team building list")
        self._say("2. Upload custom txt list (Name,Department Group)")
        self._say("3. View department groups and headcount")
        self._say("4. Load preset prize library")
        self._say("5. Add custom prize")
        self._say("6. View prize list")
        self._say("7. Set prize lottery sequence")
        self._say("8. Start lottery")
        self._say("9. View results")
        self._say("10. Export results to txt (CSV format)")
        self._say("0. Exit")

    # ----- list management -----
    def _load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._apply_loaded_users(users, errors)

    def _load_custom_list(self) -> None:
        path = self._ask("Enter the path of the txt file: ").strip().strip('"')
        users, errors = self.list_manager.load_custom_list(path)
        self._apply_loaded_users(users, errors)

    def _apply_loaded_users(self, users: list, errors: list[str]) -> None:
        if errors:
            self._say("Problems found in the list:")
            for error in errors:
                self._say(f"  - {error}")
            if not self._confirm("Remove invalid entries and continue?"):
                self._say("Upload terminated. Current list is unchanged.")
                return

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            self._say("Duplicate names detected:")
            for user in duplicates:
                self._say(f"  - {user.name} ({user.department})")
            if not self._confirm("Remove duplicate entries and continue?"):
                self._say("Upload terminated. Current list is unchanged.")
                return

        if not valid:
            self._say("No valid users to load. Current list is unchanged.")
            return

        self.users = valid
        self._say(f"Loaded {len(valid)} users successfully.")

    def _view_groups(self) -> None:
        if not self.users:
            self._say("No list loaded yet.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._say("Current department groups:")
        for group, count in info.items():
            self._say(f"  - {group}: {count} people")
        self._say(f"Total: {len(self.users)} people in {len(info)} groups")

    # ----- prize management -----
    def _load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        if errors:
            for error in errors:
                self._say(f"  - {error}")
        else:
            self._say("Preset prize library loaded.")

    def _select_avoid_groups(self) -> list[str]:
        if not self.users:
            self._say("No list loaded; no avoidance groups can be selected.")
            return []
        groups = list(self.list_manager.get_group_info(self.users).keys())
        self._say("Available groups:")
        for index, group in enumerate(groups, start=1):
            self._say(f"  {index}. {group}")
        raw = self._ask("Select avoidance groups by number, comma-separated (Enter for none): ").strip()
        selected: list[str] = []
        for token in raw.replace(" ", "").split(","):
            if not token:
                continue
            if not token.isdigit() or not 1 <= int(token) <= len(groups):
                self._say(f"Ignoring invalid selection: '{token}'")
                continue
            group = groups[int(token) - 1]
            if group not in selected:
                selected.append(group)
        return selected

    def _add_prize(self) -> None:
        name = self._ask("Prize name: ").strip()
        if not name:
            self._say("Prize name must not be empty.")
            return
        quantity_text = self._ask("Quantity: ").strip()
        try:
            quantity = int(quantity_text)
        except ValueError:
            self._say("Quantity must be an integer.")
            return
        if quantity <= 0:
            self._say("Quantity must be positive.")
            return
        drawer = self._ask("Associated lottery person (Enter for none): ").strip() or None
        avoid_groups = self._select_avoid_groups()
        try:
            self.prize_manager.add_prize(name, quantity, avoid_groups, drawer)
            self._say(f"Prize '{name}' added.")
        except ValueError as exc:
            self._say(f"Failed to add prize: {exc}")

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured.")
            return
        self._say("Prize sequence:")
        for index, prize in enumerate(prizes, start=1):
            drawer = prize.associated_drawer or "None"
            avoid = ", ".join(prize.avoid_groups) or "None"
            self._say(f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                      f"Drawer: {drawer} | Avoid groups: {avoid}")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured.")
            return
        self._view_prizes()
        raw = self._ask("Enter new order as serial numbers (e.g. 2 1 3): ").strip()
        tokens = raw.replace(",", " ").split()
        try:
            order = [int(t) for t in tokens]
        except ValueError:
            self._say("Invalid input; sequence unchanged.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._say("Prize sequence updated.")
        else:
            self._say("Invalid order; each serial number must be used exactly once.")

    # ----- lottery process -----
    def _start_lottery(self) -> None:
        if not self.users:
            self._say("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("Please configure prizes first.")
            return
        if self.result_manager.get_winners():
            if not self._confirm("Previous results will be cleared. Start a new lottery?"):
                return

        self.result_manager = ResultManager()
        self.lottery_completed = False
        lottery = LotteryManager(self.users)

        self._say("")
        self._say(f"Lottery started: {len(prizes)} rounds.")
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, prize, lottery)

        self.lottery_completed = True
        self._say("")
        self._say("All rounds completed.")
        self._show_summary(prizes)

    def _run_round(self, index: int, prize: Prize, lottery: LotteryManager) -> None:
        self._say("")
        self._say(f"===== Round {index}: {prize.name} =====")
        self._say(f"Quantity: {prize.quantity}")
        self._say(f"Rule: {describe_rule(prize)}")

        round_winners = []
        drawn = 0
        while drawn < prize.quantity:
            self._say(f"Currently drawing the {ordinal(drawn + 1)} winner...")
            command = self._ask("Press Enter to draw, or type 'pause' / 'terminate': ").strip().lower()

            if command == "terminate":
                self._say("Round terminated manually; skipping the rest of this round.")
                break
            if command == "pause":
                if not self._handle_pause():
                    self._say("Round terminated manually; skipping the rest of this round.")
                    break
                continue
            if command not in ("", "continue"):
                self._say("Unknown command.")
                continue

            user = lottery.draw(prize)
            if user is None:
                self._say("No eligible candidates remain for this prize. Round ends.")
                break
            drawn += 1
            round_winners.append(user)
            self.result_manager.add_winner(user, prize)
            self._say(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        lottery.finish_round(prize, round_winners)

        self._say(f"Round {index} results (winning order):")
        if round_winners:
            for position, user in enumerate(round_winners, start=1):
                self._say(f"  {position}. {user.name} ({user.department})")
        else:
            self._say("  No winners in this round.")

    def _handle_pause(self) -> bool:
        """Pause the lottery. Returns True to resume, False to terminate the round."""
        self._say("Lottery paused.")
        while True:
            command = self._ask("Type 'continue' to resume or 'terminate' to end this round: ").strip().lower()
            if command == "continue":
                self._say("Lottery resumed.")
                return True
            if command == "terminate":
                return False
            self._say("Unknown command.")

    def _show_summary(self, prizes: list[Prize]) -> None:
        grouped = self.result_manager.get_winners_by_prize(prizes)
        self._say("")
        self._say("===== Complete Winner List =====")
        for prize in prizes:
            self._say(f"{prize.name}:")
            winners = grouped.get(prize.name, [])
            if not winners:
                self._say("  (no winners)")
            for winner in winners:
                self._say(f"  - {winner.user.name} | {winner.user.department} | {winner.prize_name}")

    # ----- results -----
    def _view_results(self) -> None:
        if not self.result_manager.get_winners():
            self._say("No results yet.")
            return
        self._show_summary(self.prize_manager.get_prizes())

    def _export_results(self) -> None:
        if not self.result_manager.get_winners():
            self._say("No results to export yet.")
            return
        success, message = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        self._say(message)


def main() -> None:
    cli = LotteryCLI()
    try:
        cli.run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting the system.")


if __name__ == "__main__":
    main()
