"""Winner recording, ordering, display grouping and CSV export."""

from __future__ import annotations

import csv
import datetime
import os
import re
from dataclasses import dataclass

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize: Prize
    sequence: int = 0


_LEVEL_PATTERNS: list[tuple[int, re.Pattern[str]]] = [
    (1, re.compile(r"\bfirst\b", re.IGNORECASE)),
    (2, re.compile(r"\bsecond\b", re.IGNORECASE)),
    (3, re.compile(r"\bthird\b", re.IGNORECASE)),
]


def _prize_rank(prize: Prize) -> int:
    for rank, pattern in _LEVEL_PATTERNS:
        if pattern.search(prize.name):
            return rank
    return 4  # Unlabelled prizes come after the leveled ones.


def sort_prizes_by_level(prizes: list[Prize]) -> list[Prize]:
    """Sort prizes from high level (First) to low level; ties keep addition order."""
    return sorted(prizes, key=_prize_rank)


class ResultManager:
    """Keeps the complete winner history of the event."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        winner = Winner(user=user, prize=prize, sequence=len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, ordered by prize level (high to low).
        Within a prize, winners are in winning time order."""
        result: dict[str, list[Winner]] = {}
        for prize in sort_prizes_by_level(prizes):
            result[prize.name] = [
                winner for winner in self._winners if winner.prize.name == prize.name
            ]
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt as CSV."""
        date_text = datetime.datetime.now().strftime("%Y%m%d")
        path = os.path.join(os.getcwd(), f"awards_result_{date_text}.txt")
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Prize Name", "Winning Order", "Name", "Department"])
                winners_map = self.get_winners_by_prize(prizes)
                for prize_name, winners in winners_map.items():
                    for winner in winners:
                        writer.writerow(
                            [
                                prize_name,
                                winner.sequence,
                                winner.user.name,
                                winner.user.department,
                            ]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
