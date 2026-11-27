"""Result recording, summary and export."""

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple

from lottery_system.models import Prize, User

_LEVEL_KEYWORDS = [
    ("special", 0), ("grand", 1), ("first", 2), ("second", 3),
    ("third", 4), ("fourth", 5), ("fifth", 6), ("sixth", 7),
]


def prize_level(name: str) -> int:
    lower = (name or "").lower()
    for kw, rank in _LEVEL_KEYWORDS:
        if f"{kw} prize" in lower or lower.startswith(kw):
            return rank
    return 100


@dataclass
class Winner:
    user: User
    prize: Prize
    time: datetime = field(default_factory=datetime.now)
    seq: int = 0


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []
        self._seq = 0

    def add_winner(self, user: User, prize: Prize) -> bool:
        if any(w.user.name == user.name for w in self.winners):
            return False
        self._seq += 1
        self.winners.append(Winner(user, prize, datetime.now(), self._seq))
        return True

    def _sorted_prize_names(self, prizes) -> List[str]:
        names: List[str] = []
        for p in prizes or []:
            if p.name not in names:
                names.append(p.name)
        for w in self.winners:
            if w.prize.name not in names:
                names.append(w.prize.name)
        indexed = list(enumerate(names))
        indexed.sort(key=lambda t: (prize_level(t[1]), t[0]))
        return [n for _, n in indexed]

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for name in self._sorted_prize_names(prizes):
            ws = [w for w in self.winners if w.prize.name == name]
            ws.sort(key=lambda w: w.seq)
            result[name] = ws
        return result

    def export_to_csv(self, prizes) -> Tuple[bool, str]:
        if not self.winners:
            return False, "No winner records to export"
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Order", "Name", "Department", "Prize Name", "Win Time"])
                order = 0
                for name, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        order += 1
                        writer.writerow([order, w.user.name, w.user.department,
                                         name, w.time.strftime("%Y-%m-%d %H:%M:%S")])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
