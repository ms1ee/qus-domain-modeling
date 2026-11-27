"""Winner recording, grouping, sorting and CSV export."""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from datetime import date
from collections.abc import Iterable

from lottery_system.models import Prize, User, normalize

_LEVEL_WORDS = (("first", 1), ("second", 2), ("third", 3), ("fourth", 4), ("fifth", 5))
UNRANKED_LEVEL = 99


def prize_level_rank(name: str) -> int:
    """Return the level rank of a prize name (1 = highest). Unknown names rank last."""
    lowered = name.lower()
    for word, rank in _LEVEL_WORDS:
        if re.search(rf"\b{word}\b", lowered):
            return rank
    return UNRANKED_LEVEL


def sort_prizes_by_level(prizes: Iterable[Prize]) -> list[Prize]:
    """Sort prizes from high to low level, keeping original order for ties."""
    return sorted(prizes, key=lambda p: prize_level_rank(p.name))


@dataclass(frozen=True)
class Winner:
    """A single winning record."""

    user: User
    prize_name: str
    prize_order: int   # 1-based winning order within the same prize
    sequence: int      # 1-based winning order across all prizes


class ResultManager:
    """Keeps the real-time winner list and exports it."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    @property
    def winners(self) -> list[Winner]:
        return list(self._winners)

    def is_winner(self, user: User) -> bool:
        key = normalize(user.name)
        return any(normalize(w.user.name) == key for w in self._winners)

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner. Raises ValueError if the person already won."""
        if self.is_winner(user):
            raise ValueError(f"{user.name} has already won a prize.")
        prize_order = sum(1 for w in self._winners if w.prize_name == prize.name) + 1
        winner = Winner(
            user=user,
            prize_name=prize.name,
            prize_order=prize_order,
            sequence=len(self._winners) + 1,
        )
        self._winners.append(winner)
        return winner

    def get_winners_by_prize(self, prizes: Iterable[Prize]) -> dict[str, list[Winner]]:
        """Map prize name to its winners (winning time order), ordered high to low level."""
        result: dict[str, list[Winner]] = {}
        for prize in sort_prizes_by_level(prizes):
            if prize.name in result:
                continue
            result[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return result

    def export_to_csv(self, prizes: Iterable[Prize]) -> tuple[bool, str]:
        """Export the winner list to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        filename = f"awards_result_{date.today():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.writer(fh)
                writer.writerow(["Prize Level", "Prize Name", "Winning Order", "Name", "Department"])
                for prize_name, winners in grouped.items():
                    rank = prize_level_rank(prize_name)
                    level = "" if rank == UNRANKED_LEVEL else str(rank)
                    for w in winners:
                        writer.writerow([level, prize_name, w.prize_order, w.user.name, w.user.department])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
