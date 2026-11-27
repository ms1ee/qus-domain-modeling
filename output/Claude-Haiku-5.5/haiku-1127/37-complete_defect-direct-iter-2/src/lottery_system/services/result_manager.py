"""Winner recording, grouping and CSV-style export of lottery results."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record: a user who won a prize."""

    user: User
    prize: Prize

    @property
    def prize_name(self) -> str:
        return self.prize.name


class ResultManager:
    """Keeps the winner list in winning order and exports it."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> None:
        self._winners.append(Winner(user=user, prize=prize))

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name. Every given prize has a key (possibly empty list)."""
        grouped: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            grouped.setdefault(winner.prize.name, []).append(winner)
        return grouped

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        file_name = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), file_name)

        ordered: list[Winner] = []
        grouped = self.get_winners_by_prize(prizes)
        for prize in prizes:
            ordered.extend(grouped.get(prize.name, []))
        listed = {prize.name for prize in prizes}
        for winner in self._winners:
            if winner.prize.name not in listed:
                ordered.append(winner)

        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize"])
                for winner in ordered:
                    writer.writerow([winner.user.name, winner.user.department, winner.prize_name])
        except OSError as exc:
            return False, f"Export failed: {exc}"

        return True, f"Result successfully exported to {path}"
