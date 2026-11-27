"""Winner recording, ordered result summaries and CSV/txt export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date, datetime

from lottery_system.models import Prize, User, prize_level_rank


@dataclass(frozen=True)
class Winner:
    """A single winning record."""

    user: User
    prize_name: str
    sequence: int
    winning_time: str


def _prize_name(prize: Prize | str) -> str:
    return prize if isinstance(prize, str) else prize.name


def _ordered_prize_names(prizes: list[Prize] | list[str]) -> list[str]:
    """Prize names ordered by level (high to low), then by addition order."""
    indexed = list(enumerate(prizes))
    indexed.sort(key=lambda item: (prize_level_rank(_prize_name(item[1])), item[0]))
    names: list[str] = []
    for _, prize in indexed:
        name = _prize_name(prize)
        if name not in names:
            names.append(name)
    return names


class ResultManager:
    """Maintains the real-time winner list."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize | str) -> Winner:
        """Record a winner for a prize and return the winner record."""
        winner = Winner(
            user=user,
            prize_name=_prize_name(prize),
            sequence=len(self._winners) + 1,
            winning_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name.

        Keys are ordered by prize level from high to low; each list is in
        winning time order.
        """
        names = _ordered_prize_names(prizes)
        grouped: dict[str, list[Winner]] = {name: [] for name in names}
        for winner in sorted(self._winners, key=lambda w: w.sequence):
            if winner.prize_name in grouped:
                grouped[winner.prize_name].append(winner)
        return grouped

    def _ordered_winners(self, prizes: list[Prize]) -> list[Winner]:
        grouped = self.get_winners_by_prize(prizes)
        ordered = [winner for winners in grouped.values() for winner in winners]
        known = set(grouped)
        leftovers = sorted(
            (w for w in self._winners if w.prize_name not in known),
            key=lambda w: w.sequence,
        )
        return ordered + leftovers

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt.

        The file is CSV with the header Name,Department,Prize Name,Winning Time.
        Returns (success, message).
        """
        filename = f"awards_result_{date.today().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in self._ordered_winners(prizes):
                    writer.writerow(
                        [
                            winner.user.name,
                            winner.user.department,
                            winner.prize_name,
                            winner.winning_time,
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
