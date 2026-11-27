"""Winner recording, grouped summaries and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User, prize_level


@dataclass
class Winner:
    """A single winning record."""

    user: User
    prize_name: str
    winning_order: int
    winning_time: datetime


class ResultManager:
    """Stores winners and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._counter: int = 0

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for a prize and return the created record."""
        self._counter += 1
        winner = Winner(
            user=user,
            prize_name=prize.name,
            winning_order=self._counter,
            winning_time=datetime.now(),
        )
        self._winners.append(winner)
        return winner

    def all_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name.

        Keys are ordered by prize level (high to low); prizes with the same
        level keep their configured sequence. Winners within each prize are
        ordered by winning time.
        """
        ordered = sorted(
            enumerate(prizes),
            key=lambda item: (prize_level(item[1].name), item[0]),
        )
        result: dict[str, list[Winner]] = {}
        for _, prize in ordered:
            if prize.name in result:
                continue
            matched = [w for w in self._winners if w.prize_name == prize.name]
            result[prize.name] = sorted(matched, key=lambda w: w.winning_order)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list to awards_result_YYYYMMDD.txt in
        the current working directory, formatted as CSV."""
        grouped = self.get_winners_by_prize(prizes)
        rows = [winner for winners in grouped.values() for winner in winners]
        if not rows:
            return False, "No winners to export."

        file_name = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), file_name)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in rows:
                    writer.writerow(
                        [
                            winner.user.name,
                            winner.user.department,
                            winner.prize_name,
                            winner.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"

        return True, f"Winner list successfully exported to {path}"
