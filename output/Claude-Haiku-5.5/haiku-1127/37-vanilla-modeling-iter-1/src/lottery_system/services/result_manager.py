"""Winner recording, summary grouping and CSV export."""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User, sort_prizes_by_level


@dataclass
class Winner:
    """A single winning record."""

    user: User
    prize_name: str
    winning_order: int
    winning_time: str


class ResultManager:
    """Keeps the real-time winner list and exports it."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    @property
    def winners(self) -> list[Winner]:
        """All winners in winning order."""
        return list(self._winners)

    def add_winner(self, user: User, prize: Prize) -> None:
        """Record a winner for a prize."""
        record = Winner(
            user=user,
            prize_name=prize.name,
            winning_order=len(self._winners) + 1,
            winning_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._winners.append(record)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, following the order of `prizes`.

        Each list is ordered by winning order within the prize.
        """
        grouped: dict[str, list[Winner]] = {}
        for prize in prizes:
            if prize.name in grouped:
                continue
            grouped[prize.name] = sorted(
                (winner for winner in self._winners if winner.prize_name == prize.name),
                key=lambda winner: winner.winning_order,
            )
        return grouped

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to ./awards_result_YYYYMMDD.txt in CSV format.

        Rows are ordered by prize level (high to low), then winning order.
        """
        ordered_prizes = sort_prizes_by_level(prizes)
        grouped = self.get_winners_by_prize(ordered_prizes)
        file_name = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), file_name)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize in ordered_prizes:
                    for winner in grouped.get(prize.name, []):
                        writer.writerow(
                            [
                                winner.user.name,
                                winner.user.department,
                                winner.prize_name,
                                winner.winning_time,
                            ]
                        )
        except OSError as exc:
            return False, f"Export failed: cannot write '{path}': {exc}"
        return True, f"Winner list successfully exported to {path}"
