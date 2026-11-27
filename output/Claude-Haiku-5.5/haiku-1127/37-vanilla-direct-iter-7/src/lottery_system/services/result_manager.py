import os
import re
from dataclasses import dataclass
from datetime import datetime
import csv

from lottery_system.models import Prize, User

_LEVEL_WORDS = [
    "first", "second", "third", "fourth", "fifth",
    "sixth", "seventh", "eighth", "ninth", "tenth",
]
_LEVEL_PATTERN = re.compile(r"\b(" + "|".join(_LEVEL_WORDS) + r")\b", re.IGNORECASE)


def prize_level_rank(prize_name: str) -> int:
    """Lower rank means higher prize level (First=1, Second=2, Third=3...)."""
    match = _LEVEL_PATTERN.search(prize_name or "")
    if not match:
        return 99
    return _LEVEL_WORDS.index(match.group(1).lower()) + 1


def sort_prizes_by_level(prizes) -> list[Prize]:
    """Sort prizes from high to low level; ties keep addition order."""
    indexed = list(enumerate(prizes))
    indexed.sort(key=lambda item: (prize_level_rank(item[1].name), item[0]))
    return [prize for _, prize in indexed]


@dataclass
class Winner:
    user: User
    prize_name: str
    sequence: int
    won_at: str


class ResultManager:
    """Keeps the winner list in real time and produces summaries/exports."""

    def __init__(self):
        self._winners: list[Winner] = []
        self._won_keys: set[str] = set()

    @staticmethod
    def _key(user: User) -> str:
        return user.name.strip().casefold()

    def has_won(self, user: User) -> bool:
        return self._key(user) in self._won_keys

    def add_winner(self, user, prize) -> Winner:
        """Record a winner. `prize` may be a Prize or a prize name."""
        if self.has_won(user):
            raise ValueError(f"{user.name} has already won a prize.")
        prize_name = prize if isinstance(prize, str) else prize.name
        winner = Winner(
            user=user,
            prize_name=prize_name,
            sequence=len(self._winners) + 1,
            won_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._winners.append(winner)
        self._won_keys.add(self._key(user))
        return winner

    def get_all_winners(self) -> list[Winner]:
        return list(self._winners)

    def get_winners_by_prize(self, prizes) -> dict:
        """Return {prize name: [Winner...]} ordered by prize level (high to low).

        Within the same prize, winners are ordered by winning time.
        """
        result: dict[str, list[Winner]] = {}
        for prize in sort_prizes_by_level(prizes):
            matched = [w for w in self._winners if w.prize_name == prize.name]
            result[prize.name] = sorted(matched, key=lambda w: w.sequence)
        return result

    def _ordered_winners(self, prizes) -> list[Winner]:
        order_index = {}
        for index, prize in enumerate(prizes):
            order_index.setdefault(prize.name, index)
        fallback_index = len(prizes)

        def key(winner: Winner):
            return (
                prize_level_rank(winner.prize_name),
                order_index.get(winner.prize_name, fallback_index),
                winner.sequence,
            )

        return sorted(self._winners, key=key)

    def export_to_csv(self, prizes) -> tuple[bool, str]:
        """Export the complete winner list to current_dir/awards_result_YYYYMMDD.txt."""
        if not self._winners:
            return False, "No winners to export."

        filename = f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), filename)
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Name", "Department", "Prize Name", "Winning Time"])
                for winner in self._ordered_winners(prizes):
                    writer.writerow([
                        winner.user.name,
                        winner.user.department,
                        winner.prize_name,
                        winner.won_at,
                    ])
        except OSError as exc:
            return False, f"Export failed: {exc}"
        return True, f"Winner list successfully exported to {path}"
