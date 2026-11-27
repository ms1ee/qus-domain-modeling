"""Winner recording, grouping and CSV-style export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A single winning record."""

    user: User
    prize: Prize
    winning_order: int  # order of winning within the same prize (1-based)
    winning_time: datetime


class ResultManager:
    """Maintains the list of winners for the current lottery."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        order = sum(1 for winner in self._winners if winner.prize.name == prize.name) + 1
        winner = Winner(user=user, prize=prize, winning_order=order, winning_time=datetime.now())
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name; prizes ordered by level (high to low), then given order."""
        ordered = sorted(prizes, key=lambda prize: prize.level)  # stable sort
        result: dict[str, list[Winner]] = {}
        for prize in ordered:
            winners = [winner for winner in self._winners if winner.prize.name == prize.name]
            winners.sort(key=lambda winner: winner.winning_order)
            result[prize.name] = winners
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to awards_result_YYYYMMDD.txt in the current directory."""
        grouped = self.get_winners_by_prize(prizes)
        rows = [winner for winners in grouped.values() for winner in winners]
        if not rows:
            return False, "No winners to export."

        now = datetime.now()
        path = os.path.join(os.getcwd(), f"awards_result_{now:%Y%m%d}.txt")
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in rows:
                    writer.writerow([
                        winner.user.name,
                        winner.user.department,
                        winner.prize.name,
                        winner.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                    ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
