"""Command-line interface for the team building lottery."""

from __future__ import annotations

from collections.abc import Callable

from lottery_system.models import (
    DRAWER_CHOICES,
    LI_BIN,
    MA_JIAQI,
    Prize,
    User,
    normalize,
)
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


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
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None

    # ----- helpers -----------------------------------------------------

    def _ask(self, prompt: str) -> str:
        return self._input(prompt)

    def _ask_int(self, prompt: str) -> int:
        while True:
            raw = self._ask(prompt).strip()
            if raw.isdigit() and int(raw) > 0:
                return int(raw)
            self._print("Please enter a positive integer.")

    def _menu(self, title: str, options: list[str], zero_label: str = "Back") -> int:
        self._print(f"\n--- {title} ---")
        for i, option in enumerate(options, start=1):
            self._print(f"  {i}. {option}")
        self._print(f"  0. {zero_label}")
        while True:
            raw = self._ask("Select an option: ").strip()
            if raw.isdigit() and int(raw) <= len(options):
                return int(raw)
            self._print("Invalid option, please try again.")

    def _group_names(self) -> list[str]:
        return list(self.list_manager.get_group_info(self.users).keys())

    # ----- main loop ---------------------------------------------------

    def run(self) -> None:
        self._print("=" * 60)
        self._print("  Company Team Building - Smart Lottery System")
        self._print("=" * 60)
        try:
            while True:
                choice = self._menu(
                    "Main Menu",
                    [
                        "Load participant list",
                        "View group information",
                        "Configure prizes",
                        "Start lottery",
                    ],
                    zero_label="Exit",
                )
                if choice == 0:
                    break
                if choice == 1:
                    self._load_list_menu()
                elif choice == 2:
                    self._show_groups()
                elif choice == 3:
                    self._prize_menu()
                elif choice == 4:
                    self._start_lottery()
        except (EOFError, KeyboardInterrupt):
            self._print("\nExiting lottery system.")
        self._print("Goodbye!")

    # ----- participant list --------------------------------------------

    def _load_list_menu(self) -> None:
        choice = self._menu(
            "Load Participant List",
            ["Built-in default team building list", "Custom txt list"],
        )
        if choice == 1:
            users, errors = self.list_manager.load_default_list()
            self._finalize_list(users, errors)
        elif choice == 2:
            path = self._ask("Enter path of the txt file (Name,Department per line): ")
            path = path.strip().strip('"').strip("'")
            if not path:
                self._print("No path entered.")
                return
            users, errors = self.list_manager.load_custom_list(path)
            self._finalize_list(users, errors)

    def _finalize_list(self, users: list[User], errors: list[str]) -> None:
        if errors:
            self._print(f"Found {len(errors)} invalid line(s):")
            for error in errors:
                self._print(f"  {error}")

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            self._print(f"Found {len(duplicates)} duplicate name(s); first occurrence is kept:")
            for user in duplicates:
                self._print(f"  Duplicate: {user.name} ({user.department})")

        if errors or duplicates:
            while True:
                choice = self._ask(
                    "[r] Remove invalid/duplicate entries and continue, "
                    "[t] Terminate upload: "
                ).strip().lower()
                if choice in ("r", "t"):
                    break
                self._print("Please enter 'r' or 't'.")
            if choice == "t":
                self._print("Upload terminated. Previous participant list is kept.")
                return

        if not valid:
            self._print("No valid participants were loaded.")
            return

        self.users = valid
        self._print(f"Loaded {len(valid)} participant(s).")
        self._show_groups()

    def _show_groups(self) -> None:
        if not self.users:
            self._print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._print("\nValid department groups:")
        for index, (department, count) in enumerate(info.items(), start=1):
            self._print(f"  {index}. {department}: {count} people")
        self._print(f"Total: {len(self.users)} people in {len(info)} group(s)")

    # ----- prize configuration -----------------------------------------

    def _prize_menu(self) -> None:
        while True:
            choice = self._menu(
                "Prize Configuration",
                [
                    "Load default prize library",
                    "Add custom prize",
                    "Show prizes",
                    "Adjust lottery order",
                ],
            )
            if choice == 0:
                return
            if choice == 1:
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        self._print(f"  {error}")
                else:
                    self._print("Default prize library loaded.")
            elif choice == 2:
                self._add_custom_prize()
            elif choice == 3:
                self._show_prizes()
            elif choice == 4:
                self._adjust_order()

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ").strip()
        if not name:
            self._print("Prize name cannot be empty.")
            return
        quantity = self._ask_int("Quantity: ")
        drawer = self._ask(
            f"Associated lottery person ({', '.join(DRAWER_CHOICES)}; Enter for none): "
        ).strip()
        avoid_groups = self._ask_avoid_groups()
        try:
            prize = self.prize_manager.add_prize(name, quantity, avoid_groups, drawer or None)
        except ValueError as exc:
            self._print(f"Cannot add prize: {exc}")
            return
        self._print(f"Prize added: {prize.name} (quantity {prize.quantity}).")

    def _ask_avoid_groups(self) -> list[str]:
        groups = self._group_names()
        if groups:
            self._print("Available groups:")
            for index, group in enumerate(groups, start=1):
                self._print(f"  {index}. {group}")
        else:
            self._print("No participant list loaded; enter group names directly.")
        raw = self._ask("Avoided groups (numbers or names, comma-separated; Enter for none): ").strip()
        if not raw:
            return []

        selected: list[str] = []
        for token in (t.strip() for t in raw.split(",")):
            if not token:
                continue
            if groups and token.isdigit() and 1 <= int(token) <= len(groups):
                selected.append(groups[int(token) - 1])
                continue
            match = next((g for g in groups if normalize(g) == normalize(token)), token)
            if groups and match not in groups:
                self._print(f"Unknown group ignored: {token}")
                continue
            if match not in selected:
                selected.append(match)
        return selected

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        self._print("\nLottery order:")
        for index, prize in enumerate(prizes, start=1):
            self._print(
                f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                f"lottery person: {prize.associated_drawer or 'None'} | "
                f"avoid groups: {', '.join(prize.avoid_groups) or 'None'}"
            )

    def _adjust_order(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        self._show_prizes()
        raw = self._ask("New order as serial numbers, comma-separated (e.g. 2,1,3; Enter to keep): ")
        raw = raw.strip()
        if not raw:
            return
        try:
            order = [int(x) for x in raw.replace(" ", "").split(",") if x]
        except ValueError:
            self._print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._print("Lottery order updated.")
            self._show_prizes()
        else:
            self._print("Invalid order: each serial number must appear exactly once.")

    # ----- lottery process ---------------------------------------------

    def _start_lottery(self) -> None:
        if not self.users:
            self._print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("Please configure at least one prize first.")
            return

        self.lottery = LotteryManager(self.users)
        self._print("\nLottery starts!")
        self._print("Commands: [Enter] draw next | pause | continue | terminate (skip this round)")

        total = len(prizes)
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, total, prize)

        self._show_summary(prizes)
        self._offer_export(prizes)

    def _describe_rules(self, prize: Prize, lottery: LotteryManager) -> list[str]:
        drawer = normalize(prize.associated_drawer or "")
        rules = ["Previous winners cannot win again."]
        if drawer == normalize(LI_BIN):
            rules.append("Lottery person Li Bin: relaxed rules, avoidance groups are not applied.")
        elif prize.avoid_groups:
            rules.append("Avoided groups: " + ", ".join(prize.avoid_groups))
        if prize.associated_drawer:
            rules.append(f"Lottery person: {prize.associated_drawer}")
        if drawer == normalize(MA_JIAQI) and lottery.fallback_active():
            rules.append("Cheng Ru protection active: candidates limited to Cheng Ru Group members.")
        return rules

    def _run_round(self, index: int, total: int, prize: Prize) -> None:
        lottery = self.lottery
        assert lottery is not None

        self._print("")
        self._print("=" * 60)
        self._print(f"Round {index}/{total}: {prize.name}")
        self._print(f"Quantity: {prize.quantity}")
        self._print("Rules:")
        for rule in self._describe_rules(prize, lottery):
            self._print(f"  - {rule}")
        self._print(f"Eligible candidates now: {len(lottery.eligible_candidates(prize))}")

        drawn: list[User] = []
        paused = False
        while len(drawn) < prize.quantity:
            if paused:
                cmd = self._ask("Paused. Type 'continue' to resume or 'terminate' to skip: ")
            else:
                cmd = self._ask("[Enter]=draw / pause / terminate: ")
            cmd = cmd.strip().lower()

            if cmd == "terminate":
                self._print("Round terminated by operator.")
                break

            if paused:
                if cmd != "continue":
                    self._print("Lottery is paused. Type 'continue' or 'terminate'.")
                    continue
                paused = False
                self._print("Lottery resumed.")
            else:
                if cmd == "pause":
                    paused = True
                    self._print("Lottery paused. Type 'continue' to resume or 'terminate' to skip.")
                    continue
                if cmd not in ("", "continue"):
                    self._print("Unknown command. Use Enter, pause, continue or terminate.")
                    continue

            position = len(drawn) + 1
            self._print(f"Currently drawing the {ordinal(position)} winner...")
            user = lottery.draw_one(prize)
            if user is None:
                self._print("No eligible candidates remain for this prize. Round ends.")
                break
            drawn.append(user)
            self._print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        lottery.complete_round(prize, drawn)

        self._print(f"\nRound {index} results ({prize.name}):")
        if drawn:
            for number, user in enumerate(drawn, start=1):
                self._print(f"  {number}. {user.name} ({user.department})")
        else:
            self._print("  (no winners)")
        remaining = prize.quantity - len(drawn)
        if remaining > 0:
            self._print(f"Note: {remaining} award(s) of this prize were not drawn.")

    def _show_summary(self, prizes: list[Prize]) -> None:
        assert self.lottery is not None
        grouped = self.lottery.result_manager.get_winners_by_prize(prizes)
        self._print("\n" + "=" * 60)
        self._print("FINAL WINNER LIST (by prize level, high to low)")
        self._print("=" * 60)
        for prize_name, winners in grouped.items():
            self._print(f"\n[{prize_name}]")
            if not winners:
                self._print("  (no winners)")
            for winner in winners:
                self._print(
                    f"  {winner.prize_order}. {winner.user.name} "
                    f"({winner.user.department}) - {winner.prize_name}"
                )

    def _offer_export(self, prizes: list[Prize]) -> None:
        assert self.lottery is not None
        choice = self._ask("Export winner list to a txt (CSV) file? [y/N]: ").strip().lower()
        if choice in ("y", "yes"):
            _, message = self.lottery.result_manager.export_to_csv(prizes)
            self._print(message)


def main() -> int:
    LotteryCLI().run()
    return 0
