"""Result storage, ordering and export."""
import csv
import os
import re
from datetime import datetime
from typing import Dict, List

from lottery_system.models import Prize, User

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

_LEVEL_KEYWORDS = [
    (r"\bspecial\b", 0), (r"\bgrand\b", 0),
    (r"\bfirst\b", 1), (r"\bsecond\b", 2), (r"\bthird\b", 3),
    (r"\bfourth\b", 4), (r"\bfifth\b", 5),
    (r"\bconsolation\b", 50), (r"\bparticipation\b", 50),
]


def prize_level(name: str) -> int:
    lower = str(name).lower()
    for pattern, level in _LEVEL_KEYWORDS:
        if re.search(pattern, lower):
            return level
    return 100


class Winner:
    def __init__(self, user: User, prize: Prize, time: datetime = None):
        self.user = user
        self.prize = prize
        self.time = time or datetime.now()

    @property
    def time_str(self) -> str:
        return self.time.strftime(TIME_FORMAT)

    def __repr__(self):
        return f"Winner({self.user!r}, {self.prize.name!r}, {self.time_str})"


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []

    def add_winner(self, user: User, prize: Prize):
        if any(w.user.name == user.name for w in self.winners):
            return None
        winner = Winner(user, prize)
        self.winners.append(winner)
        return winner

    def clear(self):
        self.winners = []

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        prizes = list(prizes or [])
        indexed = list(enumerate(prizes))
        indexed.sort(key=lambda t: (prize_level(t[1].name), -t[0]))
        result: Dict[str, List[Winner]] = {}
        for _, p in indexed:
            result.setdefault(p.name, [])
        for w in self.winners:  # winners are stored in winning time order
            result.setdefault(w.prize.name, []).append(w)
        for name in result:
            result[name].sort(key=lambda w: w.time)
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winning results to export"
        path = os.path.join(os.getcwd(), f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt")
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize_name, winners in self.get_winners_by_prize(prizes).items():
                    for w in winners:
                        writer.writerow([w.user.name, w.user.department, prize_name, w.time_str])
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
