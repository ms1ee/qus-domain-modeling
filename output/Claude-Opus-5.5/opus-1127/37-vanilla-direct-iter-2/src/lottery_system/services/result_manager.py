"""Result storage, summary and export."""

import csv
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from lottery_system.models import Prize, User

_LEVEL_PATTERNS = [
    (r"\b(special|grand)\b", 0),
    (r"\b(first|1st)\b", 1),
    (r"\b(second|2nd)\b", 2),
    (r"\b(third|3rd)\b", 3),
    (r"\b(fourth|4th)\b", 4),
    (r"\b(fifth|5th)\b", 5),
    (r"\b(sixth|6th)\b", 6),
]


def prize_level(name: str) -> int:
    """Return a numeric level for a prize name (lower is higher level)."""
    lower = (name or "").lower()
    for pattern, level in _LEVEL_PATTERNS:
        if re.search(pattern, lower):
            return level
    return 100


def sort_prizes_by_level(prizes) -> List[Prize]:
    indexed = list(enumerate(prizes))
    indexed.sort(key=lambda t: (prize_level(t[1].name), t[0]))
    return [p for _, p in indexed]


@dataclass
class Winner:
    user: User
    prize: Prize
    win_time: datetime = field(default_factory=datetime.now)
    seq: int = 0

    @property
    def prize_name(self) -> str:
        return self.prize.name if isinstance(self.prize, Prize) else str(self.prize)


class ResultManager:
    """Keeps the winner list and provides summaries/exports."""

    def __init__(self):
        self.winners: List[Winner] = []
        self._seq = 0

    def has_won(self, user) -> bool:
        return any(w.user.name == user.name for w in self.winners)

    def winner_names(self):
        return {w.user.name for w in self.winners}

    def add_winner(self, user, prize) -> Optional[Winner]:
        if self.has_won(user):
            return None
        self._seq += 1
        winner = Winner(user=user, prize=prize, win_time=datetime.now(), seq=self._seq)
        self.winners.append(winner)
        return winner

    def clear(self):
        self.winners = []
        self._seq = 0

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for prize in sort_prizes_by_level(prizes):
            if prize.name in result:
                continue
            ws = [w for w in self.winners if w.prize_name == prize.name]
            ws.sort(key=lambda w: (w.win_time, w.seq))
            result[prize.name] = ws
        # winners for prizes not in the given list
        extra = [w for w in self.winners if w.prize_name not in result]
        for w in sorted(extra, key=lambda w: (prize_level(w.prize_name), w.win_time, w.seq)):
            result.setdefault(w.prize_name, []).append(w)
        return result

    def export_to_csv(self, prizes, path=None) -> Tuple[bool, str]:
        if path is None:
            filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
            path = os.path.join(os.getcwd(), filename)
        grouped = self.get_winners_by_prize(prizes)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for prize_name, ws in grouped.items():
                    for w in ws:
                        writer.writerow([
                            w.user.name,
                            w.user.department,
                            prize_name,
                            w.win_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
