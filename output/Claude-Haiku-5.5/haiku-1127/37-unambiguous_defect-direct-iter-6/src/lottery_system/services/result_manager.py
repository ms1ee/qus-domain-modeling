"""Winner records, grouped result summary and CSV-style export."""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from datetime import datetime

from ..models import Prize, User

_LEVEL_WORDS = (
    "first", "second", "third", "fourth", "fifth",
    "sixth", "seventh", "eighth", "ninth", "tenth",
)


def prize_level_rank(name: str) -> int:
    """Lower rank means higher prize level (e.g. 'First Prize' -> 1)."""
    for token in re.findall(r"[a-z]+", name.casefold()):
        if token in _LEVEL_WORDS:
            return _LEVEL_WORDS.index(token) + 1
    return len(_LEVEL_WORDS) + 1


@dataclass
class Winner:
    user: User
    prize_name: str


class ResultManager:
    """Keeps the winner list in winning order."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> None:
        self._winners.append(Winner(user=user, prize_name=prize.name))

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Prize names ordered from high to low level; winners in winning order."""
        indexed = sorted(
            enumerate(prizes),
            key=lambda item: (prize_level_rank(item[1].name), item[0]),
        )
        result: dict[str, list[Winner]] = {}
        for _, prize in indexed:
            if prize.name in result:
                continue
            result[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        grouped = self.get_winners_by_prize(prizes)
        filename = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Prize", "Name", "Department", "Order"])
                for prize_name, winners in grouped.items():
                    for order, winner in enumerate(winners, start=1):
                        writer.writerow(
                            [prize_name, winner.user.name, winner.user.department, order]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
