"""GameState: turns, history, ko tracking, pass/resign, termination, result.

All rule enforcement for the *flow* of the game lives here.
This object is mutable (clone() for search copies) — deliberately,
for MCTS performance. There is exactly ONE state per game; no globals.
"""
from __future__ import annotations

from collections import namedtuple

from game import rules, scoring
from game.board import BLACK, WHITE, Board, other
from game.rules import IllegalMoveError

# A move: (color, point). point is None for a pass.
Move = namedtuple("Move", ["color", "point"])

class GameOverError(Exception):
    """Raised when trying to play on a finished game."""

class GameState:
    def __init__(self, size: int = 19, komi: float = 7.5,
                 to_play: int = BLACK, board: Board = None):
        self.board = board if board is not None else Board(size)
        self.size = self.board.size
        self.komi = komi
        self.to_play = to_play

        self.move_history: list = []          # list[Move]
        self.captures = {BLACK: 0, WHITE: 0}  # stones captured BY each color
        self.ko_point = None                  # simple positional ko
        self.consecutive_passes = 0
        self.resigned_by = None
        self.game_over = False

    # ------------------------------------------------------------------ #
    # Cloning (used by MCTS)
    # ------------------------------------------------------------------ #
    def clone(self) -> "GameState":
        s = GameState.__new__(GameState)
        s.board = self.board.clone()
        s.size = self.size
        s.komi = self.komi
        s.to_play = self.to_play
        s.move_history = self.move_history[:]
        s.captures = dict(self.captures)
        s.ko_point = self.ko_point
        s.consecutive_passes = self.consecutive_passes
        s.resigned_by = self.resigned_by
        s.game_over = self.game_over
        return s

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    @property
    def move_number(self) -> int:
        return len(self.move_history)

    @property
    def last_move(self):
        return self.move_history[-1] if self.move_history else None

    def is_legal(self, point) -> bool:
        if self.game_over:
            return False
        return rules.is_point_legal(self.board, point, self.to_play, self.ko_point)

    def legal_moves(self) -> list:
        if self.game_over:
            return []
        return rules.legal_moves(self.board, self.to_play, self.ko_point)

    # ------------------------------------------------------------------ #
    # Mutations
    # ------------------------------------------------------------------ #
    def play(self, point) -> list:
        """Play a stone for `self.to_play`. Returns captured points.

        Raises IllegalMoveError / GameOverError on invalid input.
        """
        if self.game_over:
            raise GameOverError("game is already over")
        if not rules.is_point_legal(self.board, point, self.to_play, self.ko_point):
            raise IllegalMoveError(
                f"illegal move {point} for color {self.to_play} (ko={self.ko_point})"
            )

        color = self.to_play
        captured = self.board.place_and_capture(point, color)
        self.captures[color] += len(captured)

        # Simple ko detection: exactly one stone captured AND the placed
        # stone is a single-stone group with exactly one liberty.
        self.ko_point = None
        if len(captured) == 1:
            group = self.board.find_group(point)
            if len(group) == 1 and len(self.board.group_liberties(group)) == 1:
                self.ko_point = captured[0]

        self.move_history.append(Move(color, point))
        self.consecutive_passes = 0
        self.to_play = other(color)
        return captured

    def pass_turn(self) -> None:
        if self.game_over:
            raise GameOverError("game is already over")
        color = self.to_play
        self.move_history.append(Move(color, None))
        self.consecutive_passes += 1
        self.ko_point = None
        self.to_play = other(color)
        if self.consecutive_passes >= 2:
            self.game_over = True

    def resign(self) -> None:
        if self.game_over:
            raise GameOverError("game is already over")
        self.resigned_by = self.to_play
        self.game_over = True

    # ------------------------------------------------------------------ #
    # Result
    # ------------------------------------------------------------------ #
    def score(self):
        """(black_area, white_area + komi)."""
        b, w = scoring.area_score(self.board)
        return b, w + self.komi

    def winner(self):
        """BLACK / WHITE / None (None = tie or game not over & no resign)."""
        if self.resigned_by is not None:
            return other(self.resigned_by)
        if not self.game_over:
            return None
        b, w = self.score()
        if b > w:
            return BLACK
        if w > b:
            return WHITE
        return None

    def result_string(self) -> str:
        if self.resigned_by is not None:
            return "B+R" if self.resigned_by == WHITE else "W+R"
        if not self.game_over:
            return "(unfinished)"
        b, w = self.score()
        if b > w:
            return f"B+{b - w:.1f}"
        if w > b:
            return f"W+{w - b:.1f}"
        return "Draw"