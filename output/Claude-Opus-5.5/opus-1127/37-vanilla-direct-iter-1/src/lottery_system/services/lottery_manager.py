"""Lottery rule engine."""

import random

LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
CHENGRU_GROUP = "Cheng Ru group"


def _norm(text):
    return "".join(str(text or "").lower().split())


def is_chengru(department):
    d = _norm(department).replace("_", "").replace("-", "")
    return d in ("chengrugroup", "chengru")


def _same_person(a, b):
    return _norm(a) == _norm(b)


class LotteryManager:
    """Implements filtering, special rules, fallback and anti-duplication."""

    def __init__(self, users, result_manager=None, rng=None):
        self.users = list(users)
        self.result_manager = result_manager
        self.rng = rng or random.SystemRandom()
        self.winner_names = set()
        self.winners = []
        self.last_two_draw_results = []

    # ------------------------------------------------------------- rules
    def _fallback_active(self, prize):
        return (
            _same_person(prize.associated_drawer, MA_JIAQI)
            and len(self.last_two_draw_results) >= 2
            and not any(self.last_two_draw_results[-2:])
        )

    def _get_eligible_pool(self, prize):
        candidates = [u for u in self.users if u.name not in self.winner_names]
        if self._fallback_active(prize):
            return [u for u in candidates if is_chengru(u.department)]
        if _same_person(prize.associated_drawer, LI_BIN):
            return candidates
        avoid = {_norm(g) for g in prize.avoid_groups}
        return [u for u in candidates if _norm(u.department) not in avoid]

    def describe_rule(self, prize):
        parts = []
        drawer = prize.associated_drawer or "N/A"
        parts.append(f"Lottery person: {drawer}")
        if self._fallback_active(prize):
            parts.append(
                "Fallback mechanism active: prize pool limited to "
                f"'{CHENGRU_GROUP}' members (avoidance groups ignored)"
            )
        elif _same_person(prize.associated_drawer, LI_BIN):
            parts.append(
                "Special rule (Li Bin): only previous winners are excluded, "
                "avoidance groups are not applied"
            )
        else:
            if prize.avoid_groups:
                parts.append("Avoidance groups: " + ", ".join(prize.avoid_groups))
            else:
                parts.append("Avoidance groups: none")
            parts.append("Previous winners are excluded")
        return "; ".join(parts)

    # -------------------------------------------------------------- draw
    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        if user.name in self.winner_names:  # defensive anti-duplication
            return None
        self.winner_names.add(user.name)
        self.winners.append((user, prize))
        if self.result_manager is not None:
            self.result_manager.add_winner(user, prize)
        return user

    def complete_round(self, prize, round_winners):
        """Update the fallback tracking after a round has ended."""
        drawer = prize.associated_drawer
        if _same_person(drawer, CHEN_QIXIAN) or _same_person(drawer, JIN_DUO):
            hit = any(is_chengru(u.department) for u in round_winners)
            self.last_two_draw_results.append(hit)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif _same_person(drawer, MA_JIAQI):
            self.last_two_draw_results = []
