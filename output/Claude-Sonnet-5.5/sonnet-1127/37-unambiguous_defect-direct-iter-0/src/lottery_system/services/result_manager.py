import os
from datetime import datetime


class Winner:
    def __init__(self, user, prize_name, order=0):
        self.user = user
        self.prize_name = prize_name
        self.order = order


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        name = prize if isinstance(prize, str) else prize.name
        self.winners.append(Winner(user, name, len(self.winners)))

    def get_winners_by_prize(self, prizes):
        result = {}
        for p in reversed(list(prizes)):
            ws = [w for w in self.winners if w.prize_name == p.name]
            ws.sort(key=lambda w: w.order)
            result[p.name] = ws
        return result

    def export_to_csv(self, prizes):
        if not self.winners:
            return False, "No winners to export"
        path = os.path.join(os.getcwd(),
                            f"awards_result_{datetime.now().strftime('%Y%m%d')}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize\n")
                for name, ws in self.get_winners_by_prize(prizes).items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{name}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
