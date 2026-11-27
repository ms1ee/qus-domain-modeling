"""Winner bookkeeping, display and export."""

from __future__ import annotations

import csv
import os
import re
from datetime import datetime
from typing import Dict, List

from lottery_system.models import Prize, User

_LEVEL_PATTERNS = [
    (re.compile(r"\b(grand|special)\b", re.I), 0),
    (re.compile(r"\bfirst\b", re.I), 1),
    (re.compile(r"\bsecond\b", re.I), 2),
    (re.compile(r"\bthird\b", re.I), 3),
    (re.compile(r"\bfourth\b", re.I), 4),
    (re.compile(r"\bfifth\b", re.I), 5),
    (re.compile(r"\b(participation|consolation)\b", re.I), 50),
]


def prize_level(prize_name: str) -> int:
    for pattern, level in _LEVEL_PATTERNS:
        if pattern.search(prize_name):
            return level
    return 10


def sort_prizes_by_level(prizes) -> list:
    indexed = list(enumerate(prizes))
    indexed.sort(key=lambda t: (prize_level(t[1].name), t[0]))
    return [p for _, p in indexed]


class Winner:
    def __init__(self, user: User, prize: Prize, time: datetime | None = None):
        self.user = user
        self.prize = prize
        self.time = time or datetime.now()

    def __repr__(self) -> str:
        return f"Winner(user={self.user!r}, prize={self.prize.name!r})"


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []
        self._names = set()

    def add_winner(self, user: User, prize: Prize) -> bool:
        if user.name in self._names:
            return False
        self._names.add(user.name)
        self.winners.append(Winner(user, prize))
        return True

    def is_winner(self, user: User) -> bool:
        return user.name in self._names

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for prize in sort_prizes_by_level(prizes):
            result.setdefault(prize.name, [])
        for w in self.winners:
            if w.prize.name in result:
                result[w.prize.name].append(w)
        for name in result:
            result[name].sort(key=lambda w: w.time)
        return result

    def format_summary(self, prizes) -> str:
        lines = ["===== Complete Winner List ====="]
        grouped = self.get_winners_by_prize(prizes)
        any_winner = False
        for name, winners in grouped.items():
            lines.append(f"[{name}]")
            if not winners:
                lines.append("  (no winners)")
            for i, w in enumerate(winners, 1):
                any_winner = True
                lines.append(
                    f"  {i}. {w.user.name} ({w.user.department}) - {name} "
                    f"@ {w.time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
        if not any_winner:
            lines.append("No winners yet.")
        return "\n".join(lines)

    def export_to_csv(self, prizes):
        grouped = self.get_winners_by_prize(prizes)
        rows = [w for ws in grouped.values() for w in ws]
        if not rows:
            return False, "No winners to export."
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for w in rows:
                    writer.writerow(
                        [
                            w.user.name,
                            w.user.department,
                            w.prize.name,
                            w.time.strftime("%Y-%m-%d %H:%M:%S"),
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
