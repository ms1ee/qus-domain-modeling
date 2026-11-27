"""Result management: winner records, summary and export."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Dict, List


class Winner:
    """A winning record."""

    def __init__(self, user, prize_name: str, winning_time: datetime, order: int):
        self.user = user
        self.prize_name = prize_name
        self.winning_time = winning_time
        self.winning_order = order

    @property
    def name(self):
        return self.user.name

    @property
    def department(self):
        return self.user.department

    def __repr__(self):
        return f"Winner({self.user.name!r}, {self.user.department!r}, {self.prize_name!r})"


class ResultManager:
    """Maintains the list of winners."""

    def __init__(self):
        self.winners: List[Winner] = []
        self._names = set()
        self._counter = 0
        self.export_path = None

    def add_winner(self, user, prize) -> bool:
        if user.name in self._names:
            return False
        prize_name = prize.name if hasattr(prize, "name") else str(prize)
        self._counter += 1
        self.winners.append(Winner(user, prize_name, datetime.now(), self._counter))
        self._names.add(user.name)
        return True

    def has_won(self, user) -> bool:
        return user.name in self._names

    @staticmethod
    def _sorted_prizes(prizes):
        indexed = list(enumerate(prizes or []))
        indexed.sort(key=lambda t: (t[1].get_level() if hasattr(t[1], "get_level") else 100, t[0]))
        return [p for _, p in indexed]

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in self._sorted_prizes(prizes):
            name = p.name if hasattr(p, "name") else str(p)
            result[name] = []
        for w in sorted(self.winners, key=lambda w: (w.winning_time, w.winning_order)):
            result.setdefault(w.prize_name, []).append(w)
        return result

    def export_to_csv(self, prizes, path=None):
        if not self.winners:
            return False, "No winning records to export."
        if path is None:
            path = os.path.join(os.getcwd(), f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt")
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize_name, winners in grouped.items():
                    for w in winners:
                        writer.writerow([
                            w.user.name, w.user.department, prize_name,
                            w.winning_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        self.export_path = path
        return True, f"Results successfully exported to {path}"
