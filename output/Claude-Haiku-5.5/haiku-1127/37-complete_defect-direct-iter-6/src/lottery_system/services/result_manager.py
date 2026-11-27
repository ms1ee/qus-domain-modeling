"""Result management: recording winners, grouping them by prize and exporting to CSV."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from lottery_system.models import Prize, User, normalize_text


@dataclass(frozen=True)
class Winner:
    """A winning record."""

    user: User
    prize_name: str


class ResultManager:
    """Keeps the winner list in winning order and handles export."""

    CSV_HEADER: tuple[str, str, str] = ("Name", "Department", "Prize")

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> None:
        """Record a winner. Raises ValueError if the person already won."""
        key = normalize_text(user.name)
        if any(normalize_text(w.user.name) == key for w in self._winners):
            raise ValueError(f"{user.name} has already won a prize.")
        self._winners.append(Winner(user=user, prize_name=prize.name))

    def get_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, keeping winning order inside each group."""
        grouped: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize_name in grouped:
                grouped[winner.prize_name].append(winner)
        return grouped

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list to awards_result_YYYYMMDD.txt in CSV format."""
        path = Path.cwd() / f"awards_result_{datetime.now():%Y%m%d}.txt"
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(self.CSV_HEADER)
                for prize in prizes:
                    for winner in grouped.get(prize.name, []):
                        writer.writerow(
                            (winner.user.name, winner.user.department, prize.name)
                        )
        except OSError as exc:
            return False, f"Export failed: cannot write '{path}': {exc}"
        return True, f"Winner list successfully exported to {path}"
