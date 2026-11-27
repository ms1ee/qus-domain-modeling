"""Winner recording, result summaries and CSV/txt export."""

from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass, field
from datetime import datetime

from lottery_system.constants import EXPORT_FILE_PREFIX, TIME_FORMAT
from lottery_system.models import Prize, User
from lottery_system.utils import normalize_text


@dataclass
class Winner:
    """A winning record."""

    user: User
    prize: Prize
    winning_order: int = 0
    winning_time: datetime = field(default_factory=datetime.now)

    @property
    def prize_name(self) -> str:
        return self.prize.name


class ResultManager:
    """Keeps the winner list and produces summaries and exports."""

    def __init__(self) -> None:
        self._winners: list[Winner] = []
        self._won_names: set[str] = set()

    def has_won(self, user: User | str) -> bool:
        """Return True if the person (by name) has already won a prize."""
        name = user.name if isinstance(user, User) else user
        return normalize_text(name) in self._won_names

    def add_winner(self, user: User, prize: Prize) -> Winner:
        """Record a winner. Raises ValueError if the person already won."""
        if self.has_won(user):
            raise ValueError(f"{user.name} has already won a prize.")
        winner = Winner(
            user=user,
            prize=prize,
            winning_order=len(self._winners) + 1,
            winning_time=datetime.now(),
        )
        self._winners.append(winner)
        self._won_names.add(normalize_text(user.name))
        return winner

    def get_all_winners(self) -> list[Winner]:
        """Return all winners in winning order."""
        return list(self._winners)

    def get_winners_by_prize(self, prizes: list[Prize]) -> dict[str, list[Winner]]:
        """Group winners by prize name, ordered by prize level (high to low)."""
        result: dict[str, list[Winner]] = {}
        for prize in self._sorted_prizes(prizes):
            result[prize.name] = [w for w in self._winners if w.prize.name == prize.name]
        return result

    def ordered_winners(self, prizes: list[Prize]) -> list[Winner]:
        """Flatten winners by prize level (high to low), then winning order."""
        ordered: list[Winner] = []
        for prize_winners in self.get_winners_by_prize(prizes).values():
            ordered.extend(prize_winners)
        return ordered

    def export_to_csv(self, prizes: list[Prize], directory: str | None = None) -> tuple[bool, str]:
        """Export winners to ``awards_result_YYYYMMDD.txt`` in CSV format."""
        date_text = datetime.now().strftime("%Y%m%d")
        target_dir = directory or os.getcwd()
        path = os.path.join(target_dir, f"{EXPORT_FILE_PREFIX}{date_text}.txt")
        try:
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
            for winner in self.ordered_winners(prizes):
                writer.writerow([
                    winner.user.name,
                    winner.user.department,
                    winner.prize.name,
                    winner.winning_time.strftime(TIME_FORMAT),
                ])
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(buffer.getvalue())
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Results successfully exported to {path}"

    @staticmethod
    def _sorted_prizes(prizes: list[Prize]) -> list[Prize]:
        return sorted(prizes, key=lambda prize: prize.level)
