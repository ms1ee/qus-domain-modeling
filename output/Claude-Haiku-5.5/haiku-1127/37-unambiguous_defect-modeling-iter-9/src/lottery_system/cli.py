"""Command-line interface for the lottery process."""

from __future__ import annotations

from typing import Callable

from lottery_system.config import DRAWER_MA_JIAQI
from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager, describe_prize_rule
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, Winner


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryCLI:
    """Interactive console application controlling list, prize and lottery flows."""

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
        self.users: list[User] = []
        self.lottery_manager: LotteryManager | None = None
        self.lottery_done = False
        self._handlers: dict[str, Callable[[], None]] = {
            "1": self.load_default_list,
            "2": self.upload_custom_list,
            "3": self.show_groups,
            "4": self.load_default_prizes,
            "5": self.add_custom_prize,
            "6": self.set_avoid_groups,
            "7": self.show_prizes,
            "8": self.reorder_prizes,
            "9": self.start_lottery,
            "10": self.show_results,
            "11": self.export_results,
        }

    # ------------------------------------------------------------------ helpers
    def _ask(self, prompt: str) -> str:
        return self._input(prompt).strip()

    def _say(self, message: str = "") -> None:
        self._print(message)

    def _locked(self) -> bool:
        if self.lottery_done:
            self._say("The lottery has already been completed; list and prize changes are locked.")
            return True
        return False

    def _show_menu(self) -> None:
        self._say("\n========== Main Menu ==========")
        self._say("1. Load built-in default participant list")
        self._say("2. Upload custom txt participant list")
        self._say("3. View department groups and member counts")
        self._say("4. Load preset prize library")
        self._say("5. Add custom prize")
        self._say("6. Set avoidance groups for a prize")
        self._say("7. View prize configuration")
        self._say("8. Reorder prize sequence")
        self._say("9. Start lottery")
        self._say("10. View winner list")
        self._say("11. Export winner list to txt (CSV format)")
        self._say("0. Exit")

    # ------------------------------------------------------------------ main loop
    def run(self) -> None:
        self._say("=== Company Team Building Smart Lottery System ===")
        try:
            while True:
                self._show_menu()
                choice = self._ask("Select an option: ")
                if choice == "0":
                    break
                handler = self._handlers.get(choice)
                if handler is None:
                    self._say("Invalid option, please try again.")
                    continue
                handler()
        except (EOFError, KeyboardInterrupt):
            self._say("\nExiting the system.")
        self._say("Goodbye!")

    # ------------------------------------------------------------------ list management
    def load_default_list(self) -> None:
        if self._locked():
            return
        users, _ = self.list_manager.load_default_list()
        valid, _ = self.list_manager.validate_users(users)
        self.users = valid
        self._say(f"Loaded {len(valid)} participants from the built-in list.")
        self.show_groups()

    def upload_custom_list(self) -> None:
        if self._locked():
            return
        path = self._ask("Enter the path of the txt participant list: ")
        if not path:
            self._say("No path entered. Upload cancelled.")
            return

        users, errors = self.list_manager.load_custom_list(path)
        if any(e.startswith("File Error") for e in errors):
            for error in errors:
                self._say(error)
            return

        if errors:
            self._say(f"Found {len(errors)} format problem(s); these lines are invalid:")
            for error in errors:
                self._say(f"  {error}")
            choice = self._ask(
                "Type 'c' to skip these lines and continue, or 't' to terminate the upload: "
            ).lower()
            if choice != "c":
                self._say("Upload terminated.")
                return

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            self._say(f"Found {len(duplicates)} duplicate name(s):")
            for user in duplicates:
                self._say(f"  {user.name} ({user.department})")
            choice = self._ask(
                "Type 'k' to keep the first occurrence, 'm' to manually remove names, "
                "or 't' to terminate the upload: "
            ).lower()
            if choice == "m":
                raw = self._ask("Enter names to remove (comma-separated): ")
                remove = {n.strip() for n in raw.split(",") if n.strip()}
                remaining = [u for u in users if u.name not in remove]
                valid, duplicates = self.list_manager.validate_users(remaining)
                if duplicates:
                    self._say("Remaining duplicates keep their first occurrence.")
            elif choice != "k":
                self._say("Upload terminated.")
                return

        if not valid:
            self._say("No valid participants remain. Upload terminated.")
            return

        self.users = valid
        self._say(f"Loaded {len(valid)} participants from {path}.")
        self.show_groups()

    def show_groups(self) -> None:
        if not self.users:
            self._say("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._say("Department groups:")
        for group, count in info.items():
            self._say(f"  {group}: {count} member(s)")
        self._say(f"Total valid participants: {len(self.users)}")

    # ------------------------------------------------------------------ prize management
    def load_default_prizes(self) -> None:
        if self._locked():
            return
        errors = self.prize_manager.load_default_prizes()
        for error in errors:
            self._say(f"Error: {error}")
        self._say("Preset prize library loaded.")
        self.show_prizes()

    def add_custom_prize(self) -> None:
        if self._locked():
            return
        name = self._ask("Prize name: ")
        quantity_text = self._ask("Quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            self._say("Quantity must be an integer. Prize not added.")
            return
        drawer = self._ask("Associated lottery person (Chen Qixian / Jin Duo / Ma Jiaqi / Li Bin, blank for none): ")
        groups_text = self._ask("Avoidance groups (comma-separated, blank for none): ")
        groups = [g for g in groups_text.split(",")] if groups_text else []
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer or None)
        except ValueError as exc:
            self._say(f"Prize not added: {exc}")
            return
        self._say("Prize added.")
        self.show_prizes()

    def set_avoid_groups(self) -> None:
        if self._locked():
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured.")
            return
        self.show_prizes()
        index_text = self._ask("Enter the serial number of the prize: ")
        try:
            index = int(index_text)
        except ValueError:
            self._say("Invalid serial number.")
            return
        if not 1 <= index <= len(prizes):
            self._say("Serial number out of range.")
            return
        prize = prizes[index - 1]
        groups_text = self._ask("Avoidance groups (comma-separated, blank for none): ")
        groups = [g for g in groups_text.split(",")] if groups_text else []
        try:
            self.prize_manager.set_avoid_groups(prize.name, groups)
        except ValueError as exc:
            self._say(str(exc))
            return
        self._say(f"Avoidance groups updated for '{prize.name}'.")

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured.")
            return
        self._say("Prize sequence:")
        for idx, prize in enumerate(prizes, start=1):
            self._say(f"  {idx}. {prize.name} | quantity: {prize.quantity}")
            self._say(f"     Rule: {describe_prize_rule(prize)}")

    def reorder_prizes(self) -> None:
        if self._locked():
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured.")
            return
        self.show_prizes()
        raw = self._ask("Enter the new order as serial numbers (e.g. '3 1 2'): ")
        try:
            order = [int(x) for x in raw.replace(",", " ").split()]
        except ValueError:
            self._say("Invalid input; sequence unchanged.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._say("Prize sequence updated.")
            self.show_prizes()
        else:
            self._say("The order must include every serial number exactly once. Sequence unchanged.")

    # ------------------------------------------------------------------ lottery process
    def start_lottery(self) -> None:
        if self.lottery_done:
            self._say("The lottery has already been completed.")
            return
        if not self.users:
            self._say("Please load a participant list first (option 1 or 2).")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("Please configure prizes first (option 4 or 5).")
            return

        self.lottery_manager = LotteryManager(self.users)
        total = len(prizes)
        self._say("\n=== Lottery started ===")
        for idx, prize in enumerate(prizes, start=1):
            self._run_round(idx, total, prize)
        self.lottery_done = True

        self._say("\n=== Lottery completed ===")
        self._print_summary()
        choice = self._ask("Export the winner list to a txt file now? (y/n): ").lower()
        if choice == "y":
            self.export_results()

    def _await_command(self) -> str:
        """Wait for the operator's command. Returns 'draw' or 'terminate'."""
        while True:
            action = self._ask("[Enter] draw next winner | 'pause' | 'terminate': ").lower()
            if action in ("", "draw"):
                return "draw"
            if action == "terminate":
                return "terminate"
            if action == "pause":
                self._say("Lottery paused.")
                while True:
                    resume = self._ask("Type 'continue' to resume or 'terminate' to end this round: ").lower()
                    if resume == "continue":
                        self._say("Lottery resumed.")
                        break
                    if resume == "terminate":
                        return "terminate"
                    self._say("Unknown command.")
                continue
            self._say("Unknown command.")

    def _run_round(self, idx: int, total: int, prize) -> None:
        lm = self.lottery_manager
        assert lm is not None
        self._say(f"\n--- Round {idx}/{total}: {prize.name} ---")
        self._say(f"Quantity: {prize.quantity}")
        self._say(f"Rule: {describe_prize_rule(prize)}")
        if prize.associated_drawer == DRAWER_MA_JIAQI and lm.is_fallback_active():
            self._say("Fallback mechanism active: only Cheng Ru Group members are eligible this round.")

        round_winners: list[Winner] = []
        terminated = False
        for position in range(1, prize.quantity + 1):
            self._say(f"Currently drawing the {_ordinal(position)} winner of this round...")
            command = self._await_command()
            if command == "terminate":
                terminated = True
                break
            user = lm.draw_one(prize)
            if user is None:
                self._say("No eligible participants remain for this prize. Round ends.")
                break
            winner = self.result_manager.add_winner(user, prize)
            round_winners.append(winner)
            self._say(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        if terminated:
            self._say("Round terminated; remaining winners of this prize are skipped.")
        self._say(f"Round results for {prize.name}:")
        if not round_winners:
            self._say("  (no winners)")
        for winner in round_winners:
            self._say(f"  {winner.winning_order}. {winner.user.name} ({winner.user.department})")

    def _print_summary(self) -> None:
        prizes = self.prize_manager.get_prizes()
        grouped = self.result_manager.get_winners_by_prize(prizes)
        if not grouped:
            self._say("No prizes to summarize.")
            return
        self._say("\n=== Winner List (by prize level) ===")
        for prize_name, winners in grouped.items():
            self._say(f"\n{prize_name}")
            if not winners:
                self._say("  (no winners)")
            for winner in winners:
                self._say(
                    f"  #{winner.winning_order}  {winner.user.name} ({winner.user.department}) - {prize_name}"
                )

    def show_results(self) -> None:
        if not self.result_manager.get_all_winners():
            self._say("No winners recorded yet.")
            return
        self._print_summary()

    def export_results(self) -> None:
        if not self.result_manager.get_all_winners():
            self._say("No winners recorded yet; nothing to export.")
            return
        _, message = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        self._say(message)


def main() -> None:
    LotteryCLI().run()
