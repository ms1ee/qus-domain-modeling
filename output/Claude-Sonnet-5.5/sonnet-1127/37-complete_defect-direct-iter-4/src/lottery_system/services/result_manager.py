import os
from dataclasses import dataclass
from datetime import datetime

from lottery_system.models import User


@dataclass
class Winner:
    user: User
    prize_name: str = ""


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        name = prize.name if hasattr(prize, "name") else str(prize)
        self.winners.append(Winner(user, name))

    def get_winners_by_prize(self, prizes):
        result = {}
        for p in prizes:
            result[p.name] = [w for w in self.winners if w.prize_name == p.name]
        return result

    def export_to_csv(self, prizes):
        grouped = self.get_winners_by_prize(prizes)
        if not any(grouped.values()):
            return False, "No winners to export"
        path = os.path.join(os.getcwd(),
                            f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize\n")
                for p in prizes:
                    for w in grouped[p.name]:
                        f.write(f"{w.user.name},{w.user.department},{w.prize_name}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
