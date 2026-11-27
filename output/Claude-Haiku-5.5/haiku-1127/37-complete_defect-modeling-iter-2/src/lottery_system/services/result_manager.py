"""Winner recording, grouping and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize: Prize
    winning_order: int


class ResultManager:
    """Keeps the winner list and exports it."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    @property
    def winners(self) -> list[Winner]:
        return list(self._winners)

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner. The same person can never win twice."""
        if any(winner.user.name == user.name for winner in self._winners):
            raise ValueError(f"{user.name} has already won a prize")
        winner = Winner(user=user, prize=prize, winning_order=len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        grouped: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize.name in grouped:
                grouped[winner.prize.name].append(winner)
        return grouped

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export winners to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        filename = f"awards_result_{date.today():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize"])
                for prize in prizes:
                    for winner in grouped.get(prize.name, []):
                        writer.writerow(
                            [winner.user.name, winner.user.department, prize.name]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Result successfully exported to {path}"
