"""Winner recording, grouping by prize level, and CSV export."""

import csv
import os
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from lottery_system.models import User

_LEVEL_PATTERN = re.compile(r"\b(first|second|third)\b", re.IGNORECASE)
_LEVEL_RANKS = {"first": 1, "second": 2, "third": 3}
_UNRANKED = 99


def prize_level_rank(prize_name: str) -> int:
    """Return the level rank of a prize (1 = highest). Unknown levels rank last."""
    match = _LEVEL_PATTERN.search(prize_name or "")
    if match is None:
        return _UNRANKED
    return _LEVEL_RANKS[match.group(1).lower()]


def sort_prizes_by_level(prizes: list[Any]) -> list[Any]:
    """Sort prizes from high to low level; ties keep their configured order."""
    indexed = list(enumerate(prizes))
    indexed.sort(key=lambda item: (prize_level_rank(item[1].name), item[0]))
    return [prize for _, prize in indexed]


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str = ""
    order: int = 0


class ResultManager:
    """Keeps the winner list in winning order and produces summaries/exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Any) -> Winner:
        """Record a winner for a prize (a Prize object or a prize name)."""
        prize_name = prize.name if hasattr(prize, "name") else str(prize)
        winner = Winner(user=user, prize_name=prize_name, order=len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Any]) -> dict[str, list[Winner]]:
        """Group winners by prize name, ordered by prize level (high to low).

        Within each prize, winners are in winning time order.
        """
        grouped: dict[str, list[Winner]] = {}
        for prize in sort_prizes_by_level(prizes):
            grouped[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return grouped

    def export_to_csv(self, prizes: list[Any]) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt as CSV."""
        filename = f"awards_result_{date.today():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Prize Name", "Name", "Department", "Win Order"])
                for prize_name, winners in grouped.items():
                    for winner in winners:
                        writer.writerow(
                            [prize_name, winner.user.name, winner.user.department, winner.order]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
