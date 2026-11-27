from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime

from lottery_system.models import Prize, User


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    draw_order: int = 0
    win_time: datetime = field(default_factory=datetime.now)

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def department(self) -> str:
        return self.user.department


class ResultManager:
    """Stores winners and exports results."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []

    def add_winner(self, user: User, prize: Prize) -> None:
        prize_name = prize.name if isinstance(prize, Prize) else str(prize)
        self._winners.append(
            Winner(user=user, prize_name=prize_name, draw_order=len(self._winners) + 1)
        )

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        result: dict[str, list[Winner]] = {prize.name: [] for prize in prizes}
        for winner in self._winners:
            if winner.prize_name in result:
                result[winner.prize_name].append(winner)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        stamp = datetime.now().strftime("%Y%m%d")
        path = os.path.join(os.getcwd(), f"awards_result_{stamp}.txt")

        grouped = self.get_winners_by_prize(prizes)
        ordered: list[Winner] = []
        for prize in prizes:
            ordered.extend(grouped.get(prize.name, []))
        listed = {id(w) for w in ordered}
        ordered.extend(w for w in self._winners if id(w) not in listed)

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department Group", "Prize Name"])
                for winner in ordered:
                    writer.writerow([winner.name, winner.department, winner.prize_name])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
