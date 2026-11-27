"""Result management and export."""

import csv
import os
import re
from datetime import datetime

_LEVEL_WORDS = [
    ("grand", 0), ("special", 0), ("first", 1), ("1st", 1), ("second", 2), ("2nd", 2),
    ("third", 3), ("3rd", 3), ("fourth", 4), ("4th", 4), ("fifth", 5), ("5th", 5),
]


def prize_level(name):
    """Smaller value = higher prize. Unknown levels return None."""
    low = str(name).lower()
    for word, lvl in _LEVEL_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", low):
            return lvl
    return None


class Winner:
    def __init__(self, user, prize, time=None, order=0):
        self.user = user
        self.prize = prize
        self.time = time or datetime.now()
        self.order = order

    @property
    def prize_name(self):
        return self.prize.name if hasattr(self.prize, "name") else str(self.prize)

    def __repr__(self):
        return f"Winner(user={self.user!r}, prize={self.prize_name!r}, order={self.order})"


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        w = Winner(user, prize, datetime.now(), len(self.winners) + 1)
        self.winners.append(w)
        return w

    def _sorted_prize_names(self, prizes):
        names = []
        for p in prizes or []:
            n = p.name if hasattr(p, "name") else str(p)
            if n not in names:
                names.append(n)
        for w in self.winners:
            if w.prize_name not in names:
                names.append(w.prize_name)
        indexed = list(enumerate(names))

        def key(item):
            idx, n = item
            lvl = prize_level(n)
            return (lvl if lvl is not None else 100, -idx)

        return [n for _, n in sorted(indexed, key=key)]

    def get_winners_by_prize(self, prizes):
        result = {}
        for n in self._sorted_prize_names(prizes):
            result[n] = sorted(
                [w for w in self.winners if w.prize_name == n],
                key=lambda w: (w.time, w.order),
            )
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winners to export."
        path = os.path.join(os.getcwd(),
                            f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt")
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for name, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        writer.writerow([w.user.name, w.user.department, name,
                                         w.time.strftime("%Y-%m-%d %H:%M:%S")])
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
