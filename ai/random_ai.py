"""Baseline AI: uniform random choice among legal moves; pass if none."""
from __future__ import annotations

import random as _random


class RandomAI:
    name = "Random"

    def __init__(self, color: int, seed=None):
        self.color = color
        self.rng = _random.Random(seed)

    def choose_move(self, state):
        """Return a legal point, or None to pass.

        Fail-fast: raises ValueError when it is not this AI's turn.
        Returns None only when the game is already over or when no
        legal stone move exists (pass is then the only option).
        """
        if state.to_play != self.color:
            raise ValueError(
                f"RandomAI plays color {self.color} but state.to_play is "
                f"{state.to_play}"
            )
        if state.game_over:
            return None
        moves = state.legal_moves()
        if not moves:
            return None
        return self.rng.choice(moves)
