"""Lottery execution and rule engine."""

import random

from lottery_system.models import (
    CHENG_RU_GROUP,
    FALLBACK_TRIGGER_DRAWERS,
    LI_BIN,
    MA_JIAQI,
    User,
)
from lottery_system.services.result_manager import ResultManager


class LotteryManager:
    """Runs lottery rounds while applying eligibility rules."""

    DRAW_PROMPT = "Press Enter to draw the next winner, or type 'pause' / 'terminate': "
    PAUSE_PROMPT = "Lottery paused. Type 'continue' to resume or 'terminate' to end this round: "
    RETRY_PROMPT = "Please type 'continue' or 'terminate': "

    def __init__(self, users, rng=None):
        self.users: list[User] = list(users)
        self.result_manager = ResultManager()
        # Outcomes (True = a Cheng Ru group member won) of the most recent draws
        # run by Chen Qixian / Jin Duo, oldest first, at most two entries.
        self.last_two_draw_results: list[bool] = []
        self._rng = rng if rng is not None else random.SystemRandom()

    # ----------------------------------------------------------------- rules
    def _is_fallback_active(self) -> bool:
        """Fallback applies when the last two Chen/Jin draws had no Cheng Ru winner."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize) -> list[User]:
        """Return the users who may win the given prize right now."""
        taken = self.result_manager.winner_names()
        available = [user for user in self.users if user.name not in taken]

        # Special rule: Li Bin's prizes only exclude previous winners.
        if prize.associated_drawer == LI_BIN:
            return available

        # Fallback: Ma Jiaqi's pool is forced to Cheng Ru group members,
        # overriding avoidance groups. If nobody is eligible, normal rules apply.
        if prize.associated_drawer == MA_JIAQI and self._is_fallback_active():
            forced = [user for user in available if user.department == CHENG_RU_GROUP]
            if forced:
                return forced

        avoided = {group.casefold() for group in prize.avoid_groups}
        return [user for user in available if user.department.casefold() not in avoided]

    def describe_rules(self, prize) -> str:
        """Human-readable description of the rules applied to a prize round."""
        parts = ["Previous winners are excluded."]
        drawer = prize.associated_drawer
        if drawer == LI_BIN:
            parts.append("Special rule for Li Bin: avoidance groups are not applied.")
        elif drawer == MA_JIAQI and self._is_fallback_active() and any(
            user.department == CHENG_RU_GROUP and user.name not in self.result_manager.winner_names()
            for user in self.users
        ):
            parts.append(
                "Cheng Ru Group protection active: only Cheng Ru Group members are eligible "
                "(avoidance groups overridden)."
            )
        elif prize.avoid_groups:
            parts.append(f"Avoided groups: {', '.join(prize.avoid_groups)}.")
        else:
            parts.append("No avoidance groups.")
        if drawer:
            parts.append(f"Associated lottery person: {drawer}.")
        return " ".join(parts)

    # ------------------------------------------------------------ execution
    @staticmethod
    def _normalize(text) -> str:
        return (text or "").strip().lower()

    def _proceed(self, read_command) -> bool:
        """Handle pause/continue/terminate. Returns False if the round is terminated."""
        if read_command is None:
            return True
        command = self._normalize(read_command(self.DRAW_PROMPT))
        while command == "pause":
            command = self._normalize(read_command(self.PAUSE_PROMPT))
            while command not in ("continue", "terminate"):
                command = self._normalize(read_command(self.RETRY_PROMPT))
        return command != "terminate"

    def draw_prize(self, prize, read_command=None, on_drawing=None, on_winner=None) -> list[User]:
        """Run one lottery round for a prize and return its winners in order.

        read_command(prompt) -> str : supplies user commands between draws.
        on_drawing(index, total)    : called before each draw.
        on_winner(user, prize)      : called after each winner is recorded.
        """
        winners: list[User] = []
        for index in range(1, prize.quantity + 1):
            if not self._proceed(read_command):
                break
            pool = self._get_eligible_pool(prize)
            if not pool:
                break
            if on_drawing is not None:
                on_drawing(index, prize.quantity)
            winner = self._rng.choice(pool)
            self.result_manager.add_winner(winner, prize)
            winners.append(winner)
            if on_winner is not None:
                on_winner(winner, prize)

        if winners and prize.associated_drawer in FALLBACK_TRIGGER_DRAWERS:
            hit = any(user.department == CHENG_RU_GROUP for user in winners)
            self.last_two_draw_results = (self.last_two_draw_results + [hit])[-2:]
        return winners
