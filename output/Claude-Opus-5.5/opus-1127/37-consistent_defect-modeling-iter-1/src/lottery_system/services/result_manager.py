"""Winner records, summaries and export."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from lottery_system.models import Prize, User, normalize_name, prize_level_rank


@dataclass
class Winner:
    user: User
    prize_name: str
    prize: Optional[Prize] = None
    win_time: datetime = field(default_factory=datetime.now)
    draw_order: int = 0

    def __str__(self) -> str:
        return (
            f"Congratulations {self.user.name} ({self.user.department}) "
            f"for winning {self.prize_name}"
        )


class ResultManager:
    def __init__(self) -> None:
        self.winners: List[Winner] = []

    @property
    def total_winners(self) -> int:
        return len(self.winners)

    def has_won(self, user) -> bool:
        key = normalize_name(user.name)
        return any(normalize_name(w.user.name) == key for w in self.winners)

    def add_winner(self, user, prize) -> bool:
        if self.has_won(user):
            return False
        if isinstance(prize, Prize):
            name, prize_obj = prize.name, prize
        else:
            name, prize_obj = str(prize), None
        self.winners.append(
            Winner(user, name, prize_obj, datetime.now(), len(self.winners) + 1)
        )
        return True

    def _ordered_prize_names(self, prizes) -> List[str]:
        names: List[str] = []
        for p in prizes or []:
            n = p.name if isinstance(p, Prize) else str(p)
            if n not in names:
                names.append(n)
        for w in self.winners:
            if w.prize_name not in names:
                names.append(w.prize_name)
        indexed = list(enumerate(names))
        indexed.sort(key=lambda item: (prize_level_rank(item[1]), item[0]))
        return [n for _, n in indexed]

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for name in self._ordered_prize_names(prizes):
            group = [w for w in self.winners if w.prize_name == name]
            group.sort(key=lambda w: (w.win_time, w.draw_order))
            result[name] = group
        return result

    def get_sorted_winners(self, prizes) -> List[Winner]:
        out: List[Winner] = []
        for group in self.get_winners_by_prize(prizes).values():
            out.extend(group)
        return out

    def export_to_csv(self, prizes, directory: Optional[str] = None):
        if not self.winners:
            return False, "No winners to export"
        directory = directory or os.getcwd()
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(directory, filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for w in self.get_sorted_winners(prizes):
                    writer.writerow(
                        [
                            w.user.name,
                            w.user.department,
                            w.prize_name,
                            w.win_time.strftime("%Y-%m-%d %H:%M:%S"),
                        ]
                    )
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
