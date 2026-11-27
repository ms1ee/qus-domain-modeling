"""Winner records, summaries and export."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Dict, List

from lottery_system.models import User, infer_prize_level


class Winner:
    """A single winning record."""

    def __init__(self, user: User, prize_name: str, order: int, time=None):
        self.user = user
        self.prize_name = prize_name
        self.order = order
        self.time = time or datetime.now()

    @property
    def time_str(self) -> str:
        return self.time.strftime("%Y-%m-%d %H:%M:%S")

    def __repr__(self) -> str:
        return f"Winner({self.user.name}, {self.user.department}, {self.prize_name})"


class ResultManager:
    """Maintains the winner list."""

    def __init__(self) -> None:
        self.winners: List[Winner] = []

    @property
    def total_winners(self) -> int:
        return len(self.winners)

    def has_won(self, user) -> bool:
        return any(w.user.name == user.name for w in self.winners)

    def add_winner(self, user, prize):
        prize_name = getattr(prize, "name", prize)
        if self.has_won(user):
            return False
        self.winners.append(Winner(user, str(prize_name), len(self.winners) + 1))
        return True

    def clear(self) -> None:
        self.winners = []

    def _sorted_prizes(self, prizes):
        indexed = list(enumerate(prizes or []))
        indexed.sort(
            key=lambda t: (
                t[1].level if getattr(t[1], "level", None) is not None
                else infer_prize_level(t[1].name),
                t[0],
            )
        )
        return [p for _, p in indexed]

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for prize in self._sorted_prizes(prizes):
            result.setdefault(prize.name, [])
        for prize_name in result:
            items = [w for w in self.winners if w.prize_name == prize_name]
            items.sort(key=lambda w: (w.time, w.order))
            result[prize_name] = items
        return result

    def export_to_csv(self, prizes):
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        grouped = self.get_winners_by_prize(prizes)
        listed = {w for ws in grouped.values() for w in ws}
        extras = [w for w in self.winners if w not in listed]
        try:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for ws in grouped.values():
                    for w in ws:
                        writer.writerow([w.user.name, w.user.department, w.prize_name, w.time_str])
                for w in extras:
                    writer.writerow([w.user.name, w.user.department, w.prize_name, w.time_str])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
