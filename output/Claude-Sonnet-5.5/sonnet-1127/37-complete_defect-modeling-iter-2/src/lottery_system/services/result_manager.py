import datetime


class Winner:
    def __init__(self, user, prize):
        self.user = user
        self.prize = prize


class ResultManager:
    def __init__(self):
        self.winners = []

    def add_winner(self, user, prize):
        self.winners.append(Winner(user, prize))

    def get_winners_by_prize(self, prizes):
        result = {}
        for p in prizes:
            result[p.name] = [w for w in self.winners if w.prize is p
                              or getattr(w.prize, "name", w.prize) == p.name]
        return result

    def export_to_csv(self, prizes):
        fname = f"awards_result_{datetime.date.today().strftime('%Y%m%d')}.txt"
        try:
            grouped = self.get_winners_by_prize(prizes)
            with open(fname, "w", encoding="utf-8") as f:
                f.write("Name,Department,Prize\n")
                for p in prizes:
                    for w in grouped[p.name]:
                        f.write(f"{w.user.name},{w.user.department},{p.name}\n")
            return True, f"Results successfully exported to {fname}"
        except OSError as e:
            return False, f"Export failed: {e}"
