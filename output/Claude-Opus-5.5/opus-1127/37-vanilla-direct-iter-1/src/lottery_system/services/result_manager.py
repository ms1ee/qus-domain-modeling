"""Result storage, summary and export."""

import csv
import os
import re
from datetime import datetime

_LEVEL_WORDS = [
    (r"\b(special|grand)\b", 0),
    (r"\bfirst\b", 1),
    (r"\bsecond\b", 2),
    (r"\bthird\b", 3),
    (r"\bfourth\b", 4),
    (r"\bfifth\b", 5),
    (r"\bsixth\b", 6),
    (r"\b(consolation|participation|lucky)\b", 50),
]


def _prize_level(name):
    lower = str(name).lower()
    for pattern, level in _LEVEL_WORDS:
        if re.search(pattern, lower):
            return level
    return None


class Winner:
    def __init__(self, user, prize_name, time, seq):
        self.user = user
        self.prize_name = prize_name
        self.time = time
        self.seq = seq

    def __repr__(self):
        return f"Winner(user={self.user!r}, prize={self.prize_name!r})"


class ResultManager:
    def __init__(self):
        self.winners = []
        self._seq = 0

    def add_winner(self, user, prize):
        prize_name = getattr(prize, "name", prize)
        self._seq += 1
        w = Winner(user, str(prize_name), datetime.now(), self._seq)
        self.winners.append(w)
        return w

    def _ordered_prize_names(self, prizes):
        names = []
        for p in prizes or []:
            n = getattr(p, "name", p)
            if n not in names:
                names.append(n)
        for w in self.winners:
            if w.prize_name not in names:
                names.append(w.prize_name)
        count = len(names)
        keyed = []
        for idx, n in enumerate(names):
            level = _prize_level(n)
            if level is not None:
                keyed.append(((0, level, idx), n))
            else:
                # Unknown level: later rounds are considered higher prizes.
                keyed.append(((1, count - idx, idx), n))
        keyed.sort(key=lambda x: x[0])
        return [n for _, n in keyed]

    def get_winners_by_prize(self, prizes):
        result = {}
        for name in self._ordered_prize_names(prizes):
            ws = [w for w in self.winners if w.prize_name == name]
            ws.sort(key=lambda w: (w.time, w.seq))
            result[name] = ws
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winning results to export."
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for name, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        writer.writerow([
                            w.user.name,
                            w.user.department,
                            name,
                            w.time.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
