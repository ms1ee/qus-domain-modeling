"""Winner recording, summarization and CSV-style export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import Prize, User, sort_prizes_by_level


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize_name: str
    winning_time: datetime
    winning_order: int

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def department(self) -> str:
        return self.user.department


class ResultManager:
    """Keeps the complete winner list of a lottery session."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._order_counter = 0

    def add_winner(self, user: User, prize: Prize | str) -> Winner:
        prize_name = prize.name if isinstance(prize, Prize) else str(prize)
        self._order_counter += 1
        winner = Winner(
            user=user,
            prize_name=prize_name,
            winning_time=datetime.now(),
            winning_order=self._order_counter,
        )
        self._winners.append(winner)
        return winner

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Map each prize name (in the given order) to its winners in winning order."""
        result: dict[str, list[Winner]] = {}
        for prize in prizes:
            name = prize.name if isinstance(prize, Prize) else str(prize)
            matched = [winner for winner in self._winners if winner.prize_name == name]
            result[name] = sorted(matched, key=lambda winner: winner.winning_order)
        return result

    def export_to_csv(self, prizes: list[Prize]) -> tuple[bool, str]:
        """Export the winner list to awards_result_YYYYMMDD.txt in the current directory."""
        try:
            ordered_prizes = sort_prizes_by_level(prizes)
            grouped = self.get_winners_by_prize(ordered_prizes)
            date_text = datetime.now().strftime("%Y%m%d")
            path = os.path.join(os.getcwd(), f"awards_result_{date_text}.txt")
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize_name, winners in grouped.items():
                    for winner in winners:
                        writer.writerow(
                            [
                                winner.name,
                                winner.department,
                                prize_name,
                                winner.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                            ]
                        )
            return True, f"Result successfully exported to {path}"
        except OSError as exc:
            return False, f"Export failed: {exc}"
