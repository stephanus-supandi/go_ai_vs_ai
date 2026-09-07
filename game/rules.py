"""Move legality rules — pure functions over (board, point, color, ko_point).

Implemented rules:
  * move must be on board and on an empty point
  * move must not violate the (simple positional) ko rule
  * suicide is forbidden — UNLESS the move captures, which restores liberties

NOT implemented (stated explicitly):
  * positional superko / long cycles (triple ko, sending-two-returning-two).
    Only simple ko (single-stone immediate recapture) is enforced.
"""
from __future__ import annotations

from game.board import EMPTY, Board, other

class IllegalMoveError(Exception):
    """Raised when a move violates the rules."""

def _group_has_at_most_one_liberty(board: Board, point) -> bool:
    """BFS with early exit: True iff the group at `point` has <= 1 liberty."""
    color = board.get(point)
    stack = [point]
    seen = {point}
    libs = set()
    while stack:
        cur = stack.pop()
        for q in board.neighbors(cur):
            v = board.get(q)
            if v == EMPTY:
                libs.add(q)
                if len(libs) > 1:
                    return False
            elif v == color and q not in seen:
                seen.add(q)
                stack.append(q)
    return True

def is_point_legal(board: Board, point, color: int, ko_point) -> bool:
    """Is playing `color` at `point` legal on `board` (given current ko point)?

    Fast paths avoid cloning the board:
      * an empty neighbor          -> the stone has a liberty -> legal
      * an adjacent enemy group in atari -> move captures -> legal
    Otherwise we simulate (the merged friendly group may still have
    liberties elsewhere, e.g. connecting to a living group).
    """
    if not board.on_board(point):
        return False
    if board.get(point) != EMPTY:
        return False
    if ko_point is not None and point == ko_point:
        return False

    enemy = other(color)
    has_empty_neighbor = False
    captures = False
    for q in board.neighbors(point):
        v = board.get(q)
        if v == EMPTY:
            has_empty_neighbor = True
        elif v == enemy and _group_has_at_most_one_liberty(board, q):
            # group is adjacent to `point` and has <= 1 liberty,
            # so its only liberty is `point` -> it will be captured.
            captures = True

    if has_empty_neighbor or captures:
        return True

    # Expensive fallback: all neighbors occupied, no capture guaranteed.
    # Simulate to see whether the merged friendly group has any liberty.
    trial = board.clone()
    trial.place_and_capture(point, color)
    return len(trial.group_liberties(trial.find_group(point))) > 0

def legal_moves(board: Board, color: int, ko_point) -> list:
    """All legal points for `color` (passes are handled by the caller)."""
    return [p for p in board.empty_points() if is_point_legal(board, p, color, ko_point)]