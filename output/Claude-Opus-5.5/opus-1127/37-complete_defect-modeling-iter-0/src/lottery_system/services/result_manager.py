"""Winner records, summaries and export."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class Winner:
    def __init__(self, user, prize, order: int):
        self.user = user
        self.prize = prize
        self.order = order
        self.timestamp = datetime.now()

    @property
    def prize_name(self) -> str:
        return getattr(self.prize, "name", str(self.prize))

    def __repr__(self) -> str:
        return f"Winner({self.user.name!r}, {self.prize_name!r})"


class ResultManager:
    def __init__(self):
        self.winners: List[Winner] = []

    @property
    def total_winners(self) -> int:
        return len(self.winners)

    def add_winner(self, user, prize) -> bool:
        if any(w.user.name == user.name for w in self.winners):
            return False
        self.winners.append(Winner(user, prize, len(self.winners) + 1))
        return True

    def get_winners_by_prize(self, prizes) -> Dict[str, List[Winner]]:
        result: Dict[str, List[Winner]] = {}
        for p in prizes or []:
            result.setdefault(getattr(p, "name", str(p)), [])
        for w in self.winners:
            result.setdefault(w.prize_name, []).append(w)
        return result

    def export_to_csv(self, prizes, directory: Optional[str] = None) -> Tuple[bool, str]:
        if not self.winners:
            return False, "No winners to export"
        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(directory or os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Department", "Prize"])
                for name, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        writer.writerow([w.user.name, w.user.department, name])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"
