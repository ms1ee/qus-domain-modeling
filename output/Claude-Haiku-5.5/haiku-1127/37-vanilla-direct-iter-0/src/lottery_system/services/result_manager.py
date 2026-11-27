"""Winner recording, ordering, display grouping and CSV export."""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User

_LEVEL_WORDS = {
    "first": 1, "1st": 1,
    "second": 2, "2nd": 2,
    "third": 3, "3rd": 3,
    "fourth": 4, "4th": 4,
    "fifth": 5, "5th": 5,
    "sixth": 6, "6th": 6,
    "seventh": 7, "7th": 7,
    "eighth": 8, "8th": 8,
    "ninth": 9, "9th": 9,
    "tenth": 10, "10th": 10,
}


def prize_level(name: str) -> int | None:
    """Extract the prize level (1 = highest) from a prize name such as 'First Prize - ...'."""
    for token in re.findall(r"[a-z0-9]+", name.lower()):
        if token in _LEVEL_WORDS:
            return _LEVEL_WORDS[token]
    return None


def sort_prizes_by_level(prizes: list[Prize]) -> list[Prize]:
    """Sort prizes from high to low level; unknown levels go last in addition order."""

    def key(item: tuple[int, Prize]) -> tuple[bool, int, int]:
        index, prize = item
        level = prize_level(prize.name)
        return (level is None, level or 0, index)

    return [prize for _, prize in sorted(enumerate(prizes), key=key)]


@dataclass(frozen=True)
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    order: int
    win_time: str


class ResultManager:
    """Stores winners in winning order and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for the prize."""
        winner = Winner(
            user=user,
            prize_name=prize.name,
            order=len(self._winners) + 1,
            win_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        """All winners in winning order."""
        return list(self._winners)

    def _winners_for(self, prize_name: str) -> list[Winner]:
        return [winner for winner in self._winners if winner.prize_name == prize_name]

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Winners grouped by prize name, prizes ordered high to low level,
        winners within a prize in winning order."""
        result: dict[str, list[Winner]] = {}
        for prize in sort_prizes_by_level(prizes):
            result[prize.name] = self._winners_for(prize.name)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        filename = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize in sort_prizes_by_level(prizes):
                    for winner in self._winners_for(prize.name):
                        writer.writerow(
                            [
                                winner.user.name,
                                winner.user.department,
                                winner.prize_name,
                                winner.win_time,
                            ]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
