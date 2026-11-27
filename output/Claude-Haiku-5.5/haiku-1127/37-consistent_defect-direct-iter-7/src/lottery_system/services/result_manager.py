"""Winner recording, ranking and CSV export."""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import User

_ORDINAL_WORDS = [
    ("first", 1),
    ("second", 2),
    ("third", 3),
    ("fourth", 4),
    ("fifth", 5),
    ("sixth", 6),
    ("seventh", 7),
    ("eighth", 8),
    ("ninth", 9),
    ("tenth", 10),
]


def prize_level(name: str, index: int) -> int:
    """Return the prize level (1 = highest). Unknown levels sort after known ones,
    keeping their configured position."""
    lower = name.casefold()
    for word, rank in _ORDINAL_WORDS:
        if re.search(rf"\b{word}\b", lower):
            return rank
    match = re.search(r"\b(\d+)(st|nd|rd|th)\b", lower)
    if match:
        return int(match.group(1))
    return 1000 + index


@dataclass
class Winner:
    """A single winning record."""

    user: User
    prize_name: str
    sequence: int
    timestamp: str


class ResultManager:
    """Maintains the winner list in real time."""

    def __init__(self) -> None:
        self.winners: list[Winner] = []

    def add_winner(self, user: User, prize) -> Winner:
        """Record a winner. Prize may be a Prize object or a prize name.

        Raises ValueError if the person has already won (anti-duplication).
        """
        if any(w.user.name == user.name for w in self.winners):
            raise ValueError(f"{user.name} has already won a prize.")
        prize_name = prize if isinstance(prize, str) else prize.name
        winner = Winner(
            user=user,
            prize_name=prize_name,
            sequence=len(self.winners) + 1,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.winners.append(winner)
        return winner

    def get_winners_by_prize(self, prizes) -> dict[str, list[Winner]]:
        """Map prize name -> winners in winning-time order."""
        result: dict[str, list[Winner]] = {}
        for prize in prizes:
            result[prize.name] = [w for w in self.winners if w.prize_name == prize.name]
        return result

    def get_ranked_winners(self, prizes) -> list[Winner]:
        """Winners sorted by prize level (high to low), then winning time order."""
        prize_list = list(prizes)
        ranked = sorted(
            enumerate(prize_list),
            key=lambda item: (prize_level(item[1].name, item[0]), item[0]),
        )
        result: list[Winner] = []
        for _, prize in ranked:
            result.extend(w for w in self.winners if w.prize_name == prize.name)
        return result

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        """Export the ranked winner list to current_dir/awards_result_YYYYMMDD.txt."""
        filename = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in self.get_ranked_winners(prizes):
                    writer.writerow(
                        [
                            winner.user.name,
                            winner.user.department,
                            winner.prize_name,
                            winner.timestamp,
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
