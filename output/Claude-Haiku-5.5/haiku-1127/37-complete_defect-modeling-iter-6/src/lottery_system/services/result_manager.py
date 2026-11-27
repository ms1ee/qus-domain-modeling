"""Winner recording, grouping and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    draw_order: int


class ResultManager:
    """Stores winners and exports results."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> None:
        """Record a winner for a prize."""
        prize_name = getattr(prize, "name", prize)
        self._winners.append(
            Winner(user=user, prize_name=str(prize_name), draw_order=len(self._winners) + 1)
        )

    def get_all_winners(self) -> list[Winner]:
        """Return all winners in draw order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, following the given prize list."""
        result: dict[str, list[Winner]] = {}
        for prize in prizes:
            result[prize.name] = [w for w in self._winners if w.prize_name == prize.name]
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list as CSV into awards_result_YYYYMMDD.txt."""
        stamp = datetime.now().strftime("%Y%m%d")
        path = os.path.join(os.getcwd(), f"awards_result_{stamp}.txt")
        grouped = self.get_winners_by_prize(prizes)
        known_names = {p.name for p in prizes}
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize"])
                for prize in prizes:
                    for winner in grouped.get(prize.name, []):
                        writer.writerow([winner.user.name, winner.user.department, winner.prize_name])
                for winner in self._winners:
                    if winner.prize_name not in known_names:
                        writer.writerow([winner.user.name, winner.user.department, winner.prize_name])
        except OSError as exc:
            return False, f"Export failed: cannot write '{path}': {exc}"
        return True, f"Winner list successfully exported to {path}"
