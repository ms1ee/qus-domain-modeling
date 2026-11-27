import datetime
from dataclasses import dataclass


@dataclass
class Winner:
    user: object
    prize_name: str
    order: int = 0


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        self.winners.append(Winner(user, prize.name, len(self.winners) + 1))

    def get_winners_by_prize(self, prizes):
        res = {}
        for p in prizes:
            res[p.name] = [w for w in self.winners if w.prize_name == p.name]
        return res

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winners to export"
        path = f"awards_result_{datetime.date.today().strftime('%Y%m%d')}.txt"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize\n")
                for name, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{name}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
