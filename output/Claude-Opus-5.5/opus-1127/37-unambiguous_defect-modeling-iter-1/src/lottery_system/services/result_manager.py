"""Result management and export."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Dict, List

from lottery_system.models import prize_level_rank


class Winner:
    def __init__(self, user, prize, order: int, win_time: datetime = None):
        self.user = user
        self.prize = prize
        self.prize_name = getattr(prize, "name", str(prize))
        self.order = order
        self.win_time = win_time or datetime.now()

    def __repr__(self):
        return f"Winner(user={self.user!r}, prize={self.prize_name!r}, order={self.order})"


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []

    def add_winner(self, user, prize) -> bool:
        if any(w.user.name == user.name for w in self.winners):
            return False
        self.winners.append(Winner(user, prize, len(self.winners) + 1))
        return True

    def _sorted_prizes(self, prizes):
        indexed = list(enumerate(prizes))
        indexed.sort(key=lambda t: (prize_level_rank(getattr(t[1], "name", str(t[1]))), t[0]))
        return [p for _, p in indexed]

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in self._sorted_prizes(prizes):
            name = getattr(p, "name", str(p))
            ws = [w for w in self.winners if w.prize_name == name]
            ws.sort(key=lambda w: (w.win_time, w.order))
            result[name] = ws
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winners to export"
        path = os.path.join(os.getcwd(), f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt")
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Prize Name", "Name", "Department", "Win Order", "Win Time"])
                grouped = self.get_winners_by_prize(prizes)
                listed = set()
                for pname, ws in grouped.items():
                    for w in ws:
                        listed.add(id(w))
                        writer.writerow([pname, w.user.name, w.user.department, w.order,
                                         w.win_time.strftime("%Y-%m-%d %H:%M:%S")])
                for w in self.winners:
                    if id(w) not in listed:
                        writer.writerow([w.prize_name, w.user.name, w.user.department, w.order,
                                         w.win_time.strftime("%Y-%m-%d %H:%M:%S")])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
