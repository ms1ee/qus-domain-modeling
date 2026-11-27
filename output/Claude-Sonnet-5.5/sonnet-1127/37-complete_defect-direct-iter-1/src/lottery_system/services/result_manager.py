import datetime
import os


class Winner:
    def __init__(self, user, prize_name):
        self.user = user
        self.prize_name = prize_name


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        name = getattr(prize, "name", prize)
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
        fname = f"awards_result_{datetime.date.today().strftime('%Y%m%d')}.txt"
        path = os.path.join(os.getcwd(), fname)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize\n")
                for name, ws in grouped.items():
                    for w in ws:
                        f.write(f"{w.user.name},{w.user.department},{name}\n")
        except OSError as e:
            return False, f"Export failed: {e}"
        return True, f"Results successfully exported to {path}"
