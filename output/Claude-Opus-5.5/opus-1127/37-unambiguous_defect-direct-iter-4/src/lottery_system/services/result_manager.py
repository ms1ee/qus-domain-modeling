"""Result management and export."""

import csv
import os
import re
from datetime import datetime
from typing import Dict, List

LEVEL_KEYWORDS = [
    (r"\b(grand|special)\b", 0),
    (r"\bfirst\b", 1),
    (r"\bsecond\b", 2),
    (r"\bthird\b", 3),
    (r"\bfourth\b", 4),
    (r"\bfifth\b", 5),
    (r"\bsixth\b", 6),
]


def _prize_name(prize) -> str:
    return prize.name if hasattr(prize, "name") else str(prize)


def prize_level(name: str) -> int:
    low = name.lower()
    for pattern, level in LEVEL_KEYWORDS:
        if re.search(pattern, low):
            return level
    return 100


class Winner:
    def __init__(self, user, prize, sequence: int):
        self.user = user
        self.prize = prize
        self.prize_name = _prize_name(prize)
        self.sequence = sequence
        self.win_time = datetime.now()

    def __repr__(self):
        return f"Winner({self.user!r}, {self.prize_name!r})"


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []

    def add_winner(self, user, prize) -> Winner:
        w = Winner(user, prize, len(self.winners) + 1)
        self.winners.append(w)
        return w

    def _ordered_prize_names(self, prizes) -> List[str]:
        names = []
        for p in prizes or []:
            n = _prize_name(p)
            if n not in names:
                names.append(n)
        for w in self.winners:
            if w.prize_name not in names:
                names.append(w.prize_name)
        total = len(names)
        indexed = list(enumerate(names))
        # higher level first; unknown-level ties: later-drawn considered higher
        indexed.sort(key=lambda t: (prize_level(t[1]), total - t[0]))
        return [n for _, n in indexed]

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for name in self._ordered_prize_names(prizes):
            result[name] = sorted(
                [w for w in self.winners if w.prize_name == name],
                key=lambda w: w.sequence)
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winners to export."
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["No.", "Name", "Department", "Prize", "Win Time"])
                n = 0
                for prize_name, winners in self.get_winners_by_prize(prizes).items():
                    for w in winners:
                        n += 1
                        writer.writerow([n, w.user.name, w.user.department,
                                         prize_name,
                                         w.win_time.strftime("%Y-%m-%d %H:%M:%S")])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
