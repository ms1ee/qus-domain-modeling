"""Winner recording, grouping, ordering and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import User

_LEVEL_WORDS: list[tuple[str, int]] = [
    ("special", 0),
    ("grand", 0),
    ("first", 1),
    ("second", 2),
    ("third", 3),
    ("fourth", 4),
    ("fifth", 5),
    ("sixth", 6),
]


def prize_level_rank(prize_name: str) -> int:
    """Lower rank means higher prize level. Unknown levels rank last."""
    lowered = (prize_name or "").casefold()
    for word, rank in _LEVEL_WORDS:
        if word in lowered:
            return rank
    return 999


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    prize_order: int  # winning order within the same prize (1-based)
    sequence: int     # global winning order (1-based)


class ResultManager:
    """Keeps the complete winner list of a lottery run."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize) -> Winner:
        """Record a winner. `prize` is a Prize (or any object with a name)."""
        prize_name = getattr(prize, "name", str(prize))
        prize_order = sum(1 for w in self._winners if w.prize_name == prize_name) + 1
        winner = Winner(
            user=user,
            prize_name=prize_name,
            prize_order=prize_order,
            sequence=len(self._winners) + 1,
        )
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        """All winners in winning time order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes) -> dict[str, list[Winner]]:
        """Group winners by prize name, ordered from high to low prize level.
        Within each prize, winners keep their winning time order."""
        ordered_prizes = sorted(prizes, key=lambda p: prize_level_rank(p.name))
        grouped: dict[str, list[Winner]] = {}
        for prize in ordered_prizes:
            grouped[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return grouped

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        grouped = self.get_winners_by_prize(prizes)
        filename = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Prize Name", "Name", "Department", "Prize Order", "Winning Sequence"])
                for prize_name, winners in grouped.items():
                    for winner in winners:
                        writer.writerow([
                            prize_name,
                            winner.user.name,
                            winner.user.department,
                            winner.prize_order,
                            winner.sequence,
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
