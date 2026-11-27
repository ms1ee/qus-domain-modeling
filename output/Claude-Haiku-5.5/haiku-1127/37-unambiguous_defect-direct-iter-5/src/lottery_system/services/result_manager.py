"""Winner records, grouped summaries and CSV-style export."""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from datetime import date

from lottery_system.models import Prize, User

_LEVEL_PATTERN = re.compile(r"\b(First|Second|Third)\b", re.IGNORECASE)
_LEVEL_VALUES = {"first": 1, "second": 2, "third": 3}
_UNRANKED_LEVEL = 99


def prize_level_of(prize_name: str) -> int:
    """Return numeric level (1 = highest). Unrecognised names rank last."""
    match = _LEVEL_PATTERN.search(prize_name or "")
    if match is None:
        return _UNRANKED_LEVEL
    return _LEVEL_VALUES[match.group(1).lower()]


@dataclass
class Winner:
    """A single winning record."""

    user: User
    prize_name: str
    prize_level: int
    sequence: int


class ResultManager:
    """Stores winners in chronological order and produces summaries."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for a prize and return the record."""
        winner = Winner(
            user=user,
            prize_name=prize.name,
            prize_level=prize_level_of(prize.name),
            sequence=len(self._winners) + 1,
        )
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes) -> dict:
        """Return prize name -> winners, ordered by prize level (high to low).

        Within a prize, winners are in winning time order.
        """
        ordered_prizes = sorted(prizes, key=lambda prize: prize_level_of(prize.name))
        result: dict[str, list[Winner]] = {}
        for prize in ordered_prizes:
            result[prize.name] = [
                winner for winner in self._winners if winner.prize_name == prize.name
            ]
        return result

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        """Export the complete winner list to awards_result_YYYYMMDD.txt in CWD."""
        filename = f"awards_result_{date.today():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Prize Name", "Name", "Department", "Order Within Prize"])
                for prize_name, winners in self.get_winners_by_prize(prizes).items():
                    for index, winner in enumerate(winners, start=1):
                        writer.writerow(
                            [prize_name, winner.user.name, winner.user.department, index]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
