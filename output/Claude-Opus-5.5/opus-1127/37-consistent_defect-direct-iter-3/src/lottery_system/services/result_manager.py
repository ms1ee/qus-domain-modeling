"""Result management and export."""

import csv
import os
from datetime import datetime
from typing import Dict, List

from lottery_system.models import Prize, User

_LEVEL_KEYWORDS = [
    ("grand", 0), ("special", 0), ("first", 1), ("second", 2),
    ("third", 3), ("fourth", 4), ("fifth", 5), ("sixth", 6),
]


def prize_level(prize_name: str) -> int:
    lower = prize_name.lower()
    for kw, rank in _LEVEL_KEYWORDS:
        if kw in lower:
            return rank
    return 100


class Winner:
    def __init__(self, user: User, prize: Prize, time: datetime = None):
        self.user = user
        self.prize = prize
        self.time = time or datetime.now()

    def __repr__(self):
        return f"Winner({self.user.name}, {self.prize.name}, {self.time:%H:%M:%S})"


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []

    def has_won(self, user: User) -> bool:
        return any(w.user.name == user.name for w in self.winners)

    def add_winner(self, user, prize) -> bool:
        if self.has_won(user):
            return False
        self.winners.append(Winner(user, prize))
        return True

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        indexed = list(enumerate(prizes))
        indexed.sort(key=lambda t: (prize_level(t[1].name), t[0]))
        result: Dict[str, List[Winner]] = {}
        for _, p in indexed:
            if p.name in result:
                continue
            ws = [w for w in self.winners if w.prize.name == p.name]
            ws.sort(key=lambda w: w.time)
            result[p.name] = ws
        return result

    def export_to_csv(self, prizes):
        filename = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for pname, ws in grouped.items():
                    for w in ws:
                        writer.writerow([w.user.name, w.user.department, pname,
                                         w.time.strftime("%Y-%m-%d %H:%M:%S")])
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
