"""Winner recording, grouping and CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime

from ..models import Prize, User


@dataclass
class Winner:
    user: User
    prize_name: str
    winning_order: int
    won_at: datetime = field(default_factory=datetime.now)

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def department(self) -> str:
        return self.user.department


class ResultManager:
    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> Winner:
        winner = Winner(user=user, prize_name=prize.name,
                        winning_order=len(self._winners) + 1)
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        result: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            result.setdefault(winner.prize_name, []).append(winner)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        if not self._winners:
            return False, "No winners to export."
        file_name = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), file_name)
        by_prize = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize"])
                for prize_name, winners in by_prize.items():
                    for winner in sorted(winners, key=lambda w: w.winning_order):
                        writer.writerow([winner.name, winner.department, prize_name])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
