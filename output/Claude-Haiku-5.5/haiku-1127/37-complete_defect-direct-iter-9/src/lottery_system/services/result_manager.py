"""Winner tracking, grouped results and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User, normalize_key


@dataclass(frozen=True)
class Winner:
    """A winning participant and the prize name they won."""

    user: User
    prize_name: str


class ResultManager:
    """Keeps the winner list in winning order and exports it."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._winner_keys: set[str] = set()

    def add_winner(self, user: User, prize: Prize) -> None:
        """Record a winner. Raises ValueError if the person already won."""
        key = normalize_key(user.name)
        if key in self._winner_keys:
            raise ValueError(f"{user.name} has already won a prize")
        self._winner_keys.add(key)
        self._winners.append(Winner(user, prize.name))

    def get_winners(self) -> list[Winner]:
        """All winners in the order they were drawn."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, following the given prize order."""
        grouped: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize_name in grouped:
                grouped[winner.prize_name].append(winner)
        return grouped

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list to current_dir/awards_result_YYYYMMDD.txt as CSV."""
        filename = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize"])
                for prize in prizes:
                    for winner in grouped.get(prize.name, []):
                        writer.writerow(
                            [winner.user.name, winner.user.department, winner.prize_name]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
