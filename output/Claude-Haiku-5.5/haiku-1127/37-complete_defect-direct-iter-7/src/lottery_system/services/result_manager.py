"""Winner recording, grouping and CSV-style export."""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date

from lottery_system.models import Prize, User


@dataclass(frozen=True)
class Winner:
    """A winning record."""

    user: User
    prize_name: str


class ResultManager:
    """Stores winners in winning order and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for a prize."""
        winner = Winner(user=user, prize_name=prize.name)
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, following the order of the given prizes."""
        grouped: dict[str, list[Winner]] = {}
        for prize in prizes:
            grouped[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return grouped

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list to current_dir/awards_result_YYYYMMDD.txt in CSV format."""
        by_prize = self.get_winners_by_prize(prizes)
        rows = [winner for winners in by_prize.values() for winner in winners]
        if not rows:
            return False, "No winners to export."

        filename = f"awards_result_{date.today().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize"])
                for winner in rows:
                    writer.writerow([winner.user.name, winner.user.department, winner.prize_name])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
