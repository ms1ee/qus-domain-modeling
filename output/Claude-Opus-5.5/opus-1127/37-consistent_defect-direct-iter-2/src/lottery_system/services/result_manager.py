"""Result management: recording, summarising and exporting winners."""

import csv
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from lottery_system.models import Prize, User

_LEVEL_WORDS = [
    (0, ("grand", "special", "super")),
    (1, ("first", "1st")),
    (2, ("second", "2nd")),
    (3, ("third", "3rd")),
    (4, ("fourth", "4th")),
    (5, ("fifth", "5th")),
    (6, ("sixth", "6th")),
]


def prize_level(name: str) -> int:
    lowered = str(name).lower()
    for level, words in _LEVEL_WORDS:
        for w in words:
            if re.search(r"\b" + re.escape(w) + r"\b", lowered):
                return level
    return 100


@dataclass
class Winner:
    user: User
    prize_name: str
    win_time: datetime = field(default_factory=datetime.now)
    sequence: int = 0


class ResultManager:
    def __init__(self) -> None:
        self.winners: List[Winner] = []

    def add_winner(self, user, prize) -> Optional[Winner]:
        if any(w.user.name == user.name for w in self.winners):
            return None
        name = prize.name if isinstance(prize, Prize) or hasattr(prize, "name") else str(prize)
        winner = Winner(user, name, datetime.now(), len(self.winners) + 1)
        self.winners.append(winner)
        return winner

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        names: List[str] = []
        for p in prizes or []:
            n = p.name if hasattr(p, "name") else str(p)
            if n not in names:
                names.append(n)
        for w in self.winners:
            if w.prize_name not in names:
                names.append(w.prize_name)
        ordered = sorted(enumerate(names), key=lambda t: (prize_level(t[1]), t[0]))
        result: Dict[str, List[Winner]] = {}
        for _, n in ordered:
            result[n] = sorted((w for w in self.winners if w.prize_name == n),
                               key=lambda w: (w.win_time, w.sequence))
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winning results to export"
        filename = f"awards_result_{datetime.now():%Y%m%d}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize_name, winners in self.get_winners_by_prize(prizes).items():
                    for w in winners:
                        writer.writerow([w.user.name, w.user.department, prize_name,
                                         w.win_time.strftime("%Y-%m-%d %H:%M:%S")])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
