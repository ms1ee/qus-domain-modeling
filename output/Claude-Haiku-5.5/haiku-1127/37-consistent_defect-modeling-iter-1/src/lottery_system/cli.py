"""Command-line interaction for the lottery process, prizes, lists and results."""

from __future__ import annotations

import os
import re

from lottery_system.models import Prize, User, sort_prizes_by_level
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, Winner


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _split_values(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,;]", text) if part.strip()]


def describe_rules(prize: Prize) -> str:
    """Build a human readable description of the rules applied to a prize round."""
    parts: list[str] = []
    drawer = (prize.associated_drawer or "").strip()
    if drawer.casefold() == "li bin":
        parts.append("only previous winners are excluded (avoidance groups not applied)")
    else:
        parts.append("previous winners are excluded")
        if prize.avoid_groups:
            parts.append(
                "members of avoidance groups "
                f"[{', '.join(prize.avoid_groups)}] are drawn after other members"
            )
    if drawer.casefold() == "ma jiaqi":
        parts.append(
            "Cheng Ru Group protection: if the last two results of Chen Qixian and Jin Duo "
            "contain no Cheng Ru Group member, the pool is limited to Cheng Ru Group members"
        )
    if drawer:
        parts.append(f"associated lottery person: {drawer}")
    return "; ".join(parts)


class LotterySystemCLI:
    """Interactive text menu controlling the whole lottery workflow."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.list_loaded = False
        self.results = ResultManager()

    # ------------------------------------------------------------------ helpers
    def _ask(self, prompt: str) -> str:
        try:
            return input(prompt)
        except EOFError:
            print("\nInput closed. Exiting.")
            raise SystemExit(0)

    def _ask_int(self, prompt: str, minimum: int = 1) -> int:
        while True:
            text = self._ask(prompt).strip()
            try:
                value = int(text)
            except ValueError:
                print("Please enter an integer.")
                continue
            if value < minimum:
                print(f"Please enter a value >= {minimum}.")
                continue
            return value

    # --------------------------------------------------------------- main loop
    def run(self) -> None:
        print("=" * 60)
        print(" Company Team Building - Smart Lottery System")
        print("=" * 60)
        while True:
            print("\nMain Menu")
            print("  1. Load participant list")
            print("  2. View department groups")
            print("  3. Prize configuration")
            print("  4. Start lottery")
            print("  5. View / export results")
            print("  0. Exit")
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                self._menu_load_list()
            elif choice == "2":
                self._show_groups()
            elif choice == "3":
                self._menu_prizes()
            elif choice == "4":
                self._start_lottery()
            elif choice == "5":
                self._menu_results()
            elif choice == "0":
                print("Goodbye.")
                return
            else:
                print("Unknown option, please try again.")

    # ------------------------------------------------------------ list module
    def _menu_load_list(self) -> None:
        print("\nLoad participant list")
        print("  1. Built-in default team building list")
        print("  2. Upload custom txt list (format: Name,Department Group per line)")
        print("  0. Back")
        choice = self._ask("Select: ").strip()
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
            self._review_and_accept(users, errors)
        elif choice == "2":
            path = self._ask("Enter txt file path: ").strip().strip('"').strip("'")
            users, errors = self.list_manager.load_custom_list(path)
            self._review_and_accept(users, errors)

    def _review_and_accept(self, users: list[User], errors: list[str]) -> bool:
        valid, duplicates = self.list_manager.validate_users(users)
        problems = list(errors)
        problems += [
            f"Duplicate name: {user.name} ({user.department}) - entry will be ignored"
            for user in duplicates
        ]

        if not problems:
            if not valid:
                print("The list is empty. Nothing was loaded.")
                return False
            self._accept_list(valid)
            return True

        print(f"\n{len(problems)} problem(s) found:")
        for problem in problems:
            print(f"  - {problem}")
        if not valid:
            print("No valid participants remain. Upload terminated.")
            return False

        print("Options: [r] remove all invalid/duplicate data and keep the rest")
        print("         [m] remove specific names manually from the valid list")
        print("         [t] terminate upload")
        while True:
            choice = self._ask("Select [r/m/t]: ").strip().lower()
            if choice == "r":
                self._accept_list(valid)
                return True
            if choice == "m":
                names = {name.casefold() for name in _split_values(
                    self._ask("Enter names to remove (comma-separated): "))}
                remaining = [user for user in valid if user.name.casefold() not in names]
                if not remaining:
                    print("No valid participants remain. Upload terminated.")
                    return False
                self._accept_list(remaining)
                return True
            if choice == "t":
                print("Upload terminated. Previous list (if any) is unchanged.")
                return False
            print("Please choose r, m or t.")

    def _accept_list(self, users: list[User]) -> None:
        self.users = list(users)
        self.list_loaded = True
        print(f"Participant list loaded: {len(self.users)} valid participant(s).")

    def _show_groups(self) -> None:
        if not self.list_loaded:
            print("No participant list loaded yet.")
            return
        groups = self.list_manager.get_group_info(self.users)
        print("\nCurrent department groups:")
        for group, count in groups.items():
            print(f"  - {group}: {count} member(s)")

    # ----------------------------------------------------------- prize module
    def _menu_prizes(self) -> None:
        while True:
            print("\nPrize configuration")
            print("  1. View prize list")
            print("  2. Load preset prize library")
            print("  3. Add custom prize")
            print("  4. Set avoidance groups / lottery person for a prize")
            print("  5. Reorder lottery sequence")
            print("  0. Back")
            choice = self._ask("Select: ").strip()
            if choice == "1":
                self._print_prize_list()
            elif choice == "2":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    print(f"  - {error}")
                print("Preset prizes loaded.")
            elif choice == "3":
                self._add_custom_prize()
            elif choice == "4":
                self._set_prize_rules()
            elif choice == "5":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Unknown option.")

    def _print_prize_list(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nLottery sequence:")
        for position, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            print(
                f"  {position}. {prize.name} | quantity: {prize.quantity} | "
                f"avoid groups: {groups} | lottery person: {drawer}"
            )

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ").strip()
        quantity = self._ask_int("Quantity: ")
        groups_text = self._ask("Avoidance groups (comma-separated, blank for none): ")
        groups = _split_values(groups_text)
        drawer = self._ask("Associated lottery person (blank for none): ").strip()
        try:
            prize = self.prize_manager.add_prize(name, quantity, groups, drawer or None)
            print(f"Prize added: {prize.name}")
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")

    def _set_prize_rules(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._print_prize_list()
        index = self._ask_int("Prize number to configure: ") - 1
        if index < 0 or index >= len(prizes):
            print("Invalid prize number.")
            return
        groups = _split_values(self._ask("Avoidance groups (comma-separated, blank for none): "))
        drawer = self._ask("Associated lottery person (blank for none): ").strip()
        self.prize_manager.set_rules(index, groups, drawer or None)
        print("Prize rules updated.")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._print_prize_list()
        text = self._ask(
            "Enter new order as serial numbers separated by spaces or commas (e.g. 2 1 3): "
        )
        order = [int(value) for value in re.findall(r"\d+", text)]
        if self.prize_manager.reorder_prizes(order):
            print("Lottery sequence updated.")
        else:
            print("Invalid order: every serial number must appear exactly once.")

    # ------------------------------------------------------- lottery process
    def _start_lottery(self) -> None:
        if not self.list_loaded or not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure at least one prize first.")
            return

        confirm = self._ask("Start the lottery now? [y/n]: ").strip().lower()
        if confirm != "y":
            return

        lottery = LotteryManager(self.users)
        self.results = ResultManager()
        total_rounds = len(prizes)
        for round_number, prize in enumerate(prizes, start=1):
            self._run_round(round_number, total_rounds, prize, lottery)

        print("\n" + "=" * 60)
        print(" Lottery finished. Final winner list:")
        print("=" * 60)
        self._print_results(prizes)

    def _run_round(
        self,
        round_number: int,
        total_rounds: int,
        prize: Prize,
        lottery: LotteryManager,
    ) -> None:
        print("\n" + "-" * 60)
        print(
            f"Round {round_number}/{total_rounds}: {prize.name} | "
            f"Quantity: {prize.quantity}"
        )
        print(f"Rule: {describe_rules(prize)}")
        print("-" * 60)

        round_winners: list[Winner] = []
        for draw_index in range(1, prize.quantity + 1):
            command = self._wait_for_command()
            if command == "terminate":
                print("Current round terminated. Skipping to the next round.")
                break

            print(f"Currently drawing the {_ordinal(draw_index)} winner...")
            user = lottery.draw(prize)
            if user is None:
                print("No eligible participants remain for this prize. Round ends.")
                break
            winner = self.results.add_winner(user, prize)
            round_winners.append(winner)
            print(
                f"Congratulations {user.name} ({user.department}) for winning {prize.name}!"
            )

        print(f"\nRound {round_number} results ({len(round_winners)} winner(s)):")
        if not round_winners:
            print("  (no winners in this round)")
        for winner in round_winners:
            print(f"  {winner.winning_order}. {winner.name} ({winner.department}) - {prize.name}")

    def _wait_for_command(self) -> str:
        """Return 'draw' or 'terminate'. Supports pause/continue/terminate commands."""
        while True:
            command = self._ask(
                "[Enter] draw next | 'pause' | 'terminate' > "
            ).strip().lower()
            if command in ("", "draw", "continue"):
                return "draw"
            if command == "terminate":
                return "terminate"
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    resume = self._ask("paused > ").strip().lower()
                    if resume == "continue":
                        print("Lottery resumed.")
                        return "draw"
                    if resume == "terminate":
                        return "terminate"
                    print("Type 'continue' or 'terminate'.")
            print("Unknown command. Press Enter to draw, or type 'pause' or 'terminate'.")

    # ---------------------------------------------------------- results
    def _print_results(self, prizes: list[Prize]) -> None:
        grouped = self.results.get_winners_by_prize(sort_prizes_by_level(prizes))
        if not any(grouped.values()):
            print("No winners recorded.")
            return
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            print(f"\n{prize_name}:")
            for winner in winners:
                print(
                    f"  {winner.winning_order}. {winner.name} ({winner.department}) "
                    f"- {winner.winning_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )

    def _menu_results(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not self.results.get_all_winners():
            print("No results yet. Run the lottery first.")
            return
        print("\nResults")
        print("  1. Show winner list")
        print("  2. Export winner list to txt (CSV format)")
        print("  0. Back")
        choice = self._ask("Select: ").strip()
        if choice == "1":
            self._print_results(prizes)
        elif choice == "2":
            _, message = self.results.export_to_csv(prizes)
            print(message)


def main() -> None:
    """Application entry point."""
    try:
        LotterySystemCLI().run()
    except (KeyboardInterrupt, SystemExit):
        print("\nExiting lottery system.")
