import csv
import os
import re
from datetime import datetime
from typing import Dict, List

_LEVELS = [
    (r"\b(grand|special|super)\b", 0),
    (r"\bfirst\b", 1),
    (r"\bsecond\b", 2),
    (r"\bthird\b", 3),
    (r"\bfourth\b", 4),
    (r"\bfifth\b", 5),
    (r"\bsixth\b", 6),
    (r"\bconsolation\b|\bparticipation\b|\blucky\b", 50),
]


def prize_level(name: str) -> int:
    lower = name.lower()
    for pattern, level in _LEVELS:
        if re.search(pattern, lower):
            return level
    return 100


def sort_prizes_by_level(prizes) -> list:
    indexed = list(enumerate(prizes))
    indexed.sort(key=lambda t: (prize_level(t[1].name), t[0]))
    return [p for _, p in indexed]


class Winner:
    def __init__(self, user, prize, time=None, seq=0):
        self.user = user
        self.prize = prize
        self.time = time or datetime.now()
        self.seq = seq

    @property
    def prize_name(self):
        return self.prize.name if hasattr(self.prize, "name") else str(self.prize)

    def __repr__(self):
        return f"Winner({self.user!r}, {self.prize_name!r}, {self.time})"


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []
        self._seq = 0

    def has_won(self, user) -> bool:
        return any(w.user.name == user.name for w in self.winners)

    def add_winner(self, user, prize):
        if self.has_won(user):
            return False
        self._seq += 1
        self.winners.append(Winner(user, prize, datetime.now(), self._seq))
        return True

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in prizes:
            result[p.name] = []
        for w in sorted(self.winners, key=lambda x: (x.time, x.seq)):
            result.setdefault(w.prize_name, []).append(w)
        return result

    def get_summary(self, prizes):
        """Ordered list of (prize_name, [Winner]) by prize level high->low."""
        by_prize = self.get_winners_by_prize(prizes)
        ordered = []
        for p in sort_prizes_by_level(prizes):
            ordered.append((p.name, by_prize.get(p.name, [])))
        known = {p.name for p in prizes}
        for name, ws in by_prize.items():
            if name not in known:
                ordered.append((name, ws))
        return ordered

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winners to export."
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize_name, ws in self.get_summary(prizes):
                    for w in ws:
                        writer.writerow([
                            w.user.name,
                            w.user.department,
                            prize_name,
                            w.time.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
