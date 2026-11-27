"""Winner recording, grouped summaries and CSV-style export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime

from lottery_system.models import Prize, User

EXPORT_HEADER = ["Prize Level", "Prize Name", "Winning Order", "Name", "Department"]


@dataclass
class Winner:
    """A single winning record."""

    user: User
    prize: Prize
    winning_order: int
    won_at: datetime = field(default_factory=datetime.now)


class ResultManager:
    """Stores winners in winning order and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    @property
    def winners(self) -> list[Winner]:
        """All winners in the order they were drawn."""
        return list(self._winners)

    def clear(self) -> None:
        """Remove all recorded winners."""
        self._winners.clear()

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner for a prize. Winning order is global and 1-based."""
        winner = Winner(user=user, prize=prize, winning_order=len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name.

        Keys are ordered by prize level from high to low (level 1 first), with
        ties broken by the configured prize order. Within each prize, winners
        are in winning time order.
        """
        ordered = sorted(enumerate(prizes), key=lambda item: (item[1].level, item[0]))
        grouped: dict[str, list[Winner]] = {}
        for _, prize in ordered:
            grouped[prize.name] = [w for w in self._winners if w.prize.name == prize.name]
        return grouped

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list to awards_result_YYYYMMDD.txt in the current directory."""
        if not self._winners:
            return False, "No winners to export."

        file_name = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), file_name)
        grouped = self.get_winners_by_prize(prizes)

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(EXPORT_HEADER)
                for winners in grouped.values():
                    for winner in winners:
                        writer.writerow([
                            winner.prize.level,
                            winner.prize.name,
                            winner.winning_order,
                            winner.user.name,
                            winner.user.department,
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"

        return True, f"Winner list successfully exported to {path}"
