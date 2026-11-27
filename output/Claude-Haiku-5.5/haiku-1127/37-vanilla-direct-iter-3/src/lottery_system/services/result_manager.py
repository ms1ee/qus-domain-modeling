"""Winner recording, ordering, display support and CSV export."""

from __future__ import annotations

import csv
import datetime
import os
import re
from dataclasses import dataclass, field

from lottery_system.config import RESULT_FILE_PREFIX
from lottery_system.models import Prize, User

_UNRANKED = 1000

# Keywords identifying prize level; lower rank = higher level.
_LEVEL_KEYWORDS: tuple[tuple[str, int], ...] = (
    ("grand", 0),
    ("special", 0),
    ("first", 1),
    ("1st", 1),
    ("second", 2),
    ("2nd", 2),
    ("third", 3),
    ("3rd", 3),
    ("fourth", 4),
    ("4th", 4),
    ("fifth", 5),
    ("5th", 5),
)

_CSV_HEADER = ["Name", "Department", "Prize Name", "Winning Time"]


def prize_level_rank(prize_name: str) -> int:
    """Return the level rank of a prize name (0 = highest). Unknown levels rank last."""
    lowered = (prize_name or "").casefold()
    for keyword, rank in _LEVEL_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            return rank
    return _UNRANKED


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    sequence: int
    won_at: datetime.datetime = field(default_factory=datetime.datetime.now)


class ResultManager:
    """Keeps all winners in winning order and produces summaries/exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._sequence = 0

    def add_winner(self, user: User, prize: Prize) -> Winner:
        self._sequence += 1
        winner = Winner(user=user, prize_name=prize.name, sequence=self._sequence)
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize, ordered by prize level (high to low).

        Within a prize, winners are in winning time order.
        """
        ordered = sorted(prizes, key=lambda prize: prize_level_rank(prize.name))
        result: dict[str, list[Winner]] = {}
        for prize in ordered:
            result[prize.name] = [
                winner for winner in self._winners if winner.prize_name == prize.name
            ]
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to <cwd>/awards_result_YYYYMMDD.txt in CSV format."""
        filename = f"{RESULT_FILE_PREFIX}{datetime.datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(_CSV_HEADER)
                for prize_name, winners in self.get_winners_by_prize(prizes).items():
                    for winner in winners:
                        writer.writerow(
                            [
                                winner.user.name,
                                winner.user.department,
                                prize_name,
                                winner.won_at.strftime("%Y-%m-%d %H:%M:%S"),
                            ]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
