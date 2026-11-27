"""Result recording, summarizing and export."""

import csv
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from lottery_system.models import Prize, User

_LEVEL_PATTERNS = [
    (re.compile(r"\b(special|grand)\b", re.I), 0),
    (re.compile(r"\bfirst\b", re.I), 1),
    (re.compile(r"\bsecond\b", re.I), 2),
    (re.compile(r"\bthird\b", re.I), 3),
    (re.compile(r"\bfourth\b", re.I), 4),
    (re.compile(r"\bfifth\b", re.I), 5),
    (re.compile(r"\b(consolation|participation)\b", re.I), 50),
]


def prize_level(name: str) -> int:
    """Lower value means higher prize level."""
    for pattern, level in _LEVEL_PATTERNS:
        if pattern.search(name):
            return level
    return 40


class Winner:
    def __init__(self, user: User, prize_name: str, order: int, prize: Optional[Prize] = None):
        self.user = user
        self.prize_name = prize_name
        self.prize = prize
        self.order = order
        self.time = datetime.now()

    def __repr__(self) -> str:
        return f"Winner({self.user!r}, {self.prize_name!r}, order={self.order})"


def _prize_name(prize) -> str:
    return prize.name if isinstance(prize, Prize) else str(prize)


class ResultManager:
    def __init__(self) -> None:
        self.winners: List[Winner] = []
        self._counter = 0

    def has_won(self, user: User) -> bool:
        key = user.name.strip().lower()
        return any(w.user.name.strip().lower() == key for w in self.winners)

    def add_winner(self, user, prize) -> bool:
        if self.has_won(user):
            return False
        self._counter += 1
        self.winners.append(
            Winner(user, _prize_name(prize), self._counter, prize if isinstance(prize, Prize) else None)
        )
        return True

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        names: List[str] = []
        for p in prizes or []:
            n = _prize_name(p)
            if n not in names:
                names.append(n)
        for w in self.winners:
            if w.prize_name not in names:
                names.append(w.prize_name)
        ordered = sorted(enumerate(names), key=lambda t: (prize_level(t[1]), t[0]))
        result: Dict[str, List[Winner]] = {}
        for _, n in ordered:
            result[n] = sorted((w for w in self.winners if w.prize_name == n), key=lambda w: w.order)
        return result

    def export_to_csv(self, prizes, output_dir: Optional[str] = None):
        directory = output_dir or os.getcwd()
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(directory, filename)
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["No.", "Name", "Department", "Prize", "Win Time"])
                no = 0
                for prize_name, winners in grouped.items():
                    for w in winners:
                        no += 1
                        writer.writerow([
                            no, w.user.name, w.user.department, prize_name,
                            w.time.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
