"""Winner recording, grouping and CSV export."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from lottery_system.models import Prize, User, sort_prizes_by_level


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    order: int


class ResultManager:
    """Stores winners in the order they were drawn."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize | str) -> Winner:
        prize_name = prize if isinstance(prize, str) else prize.name
        winner = Winner(user=user, prize_name=prize_name, order=len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Map prize name -> winners in winning order, following the given prize order."""
        grouped: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize_name in grouped:
                grouped[winner.prize_name].append(winner)
        return grouped

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the complete winner list to current_dir/awards_result_YYYYMMDD.txt."""
        path = Path.cwd() / f"awards_result_{date.today():%Y%m%d}.txt"
        ordered = sort_prizes_by_level(prizes)
        grouped = self.get_winners_by_prize(ordered)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Prize Name", "Winning Order", "Name", "Department"])
                for prize in ordered:
                    for position, winner in enumerate(grouped[prize.name], start=1):
                        writer.writerow(
                            [
                                prize.name,
                                position,
                                winner.user.name,
                                winner.user.department,
                            ]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
