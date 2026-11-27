"""Winner recording, summary grouping and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User, prize_level


@dataclass
class Winner:
    """A single winning record."""

    user: User
    prize: Prize
    winning_order: int


class ResultManager:
    """Keeps the winner list in winning time order and produces summaries."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        winner = Winner(user=user, prize=prize, winning_order=len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, ordered from highest to lowest prize level.

        Within the same prize, winners keep their winning time order.
        """
        ordered_prizes = sorted(prizes, key=prize_level)
        result: dict[str, list[Winner]] = {}
        for prize in ordered_prizes:
            if prize.name in result:
                continue
            result[prize.name] = [w for w in self._winners if w.prize.name == prize.name]
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        if not self._winners:
            return False, "No winners to export."

        filename = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Prize Name", "Name", "Department", "Winning Order"])
                for prize_name, winners in self.get_winners_by_prize(prizes).items():
                    for winner in winners:
                        writer.writerow(
                            [
                                prize_name,
                                winner.user.name,
                                winner.user.department,
                                winner.winning_order,
                            ]
                        )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
