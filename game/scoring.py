"""Area scoring (simplified Tromp–Taylor style).

score(color) = stones of that color on the board
             + empty regions whose bordering stones are ALL that color.

Neutral (dame) regions border both colors and count for nobody.

Limitation (stated explicitly): there is no dead-stone agreement/removal
phase and no seki detection. Groups that are "dead" by human judgment but
not captured during play are counted as alive. AI-vs-AI games must be
played out until captures resolve this (random/MCTS rollouts do fill and
capture most dead stones eventually).
"""
from __future__ import annotations

from game.board import BLACK, EMPTY, WHITE, Board

def area_score(board: Board):
    """Return (black_area, white_area) WITHOUT komi."""
    black_area = 0
    white_area = 0
    for r in range(board.size):
        for c in range(board.size):
            v = board.grid[r][c]
            if v == BLACK:
                black_area += 1
            elif v == WHITE:
                white_area += 1

    visited = set()
    for r in range(board.size):
        for c in range(board.size):
            start = (r, c)
            if board.get(start) != EMPTY or start in visited:
                continue
            # flood-fill the empty region, collecting border colors
            stack = [start]
            visited.add(start)
            region = []
            borders = set()
            while stack:
                cur = stack.pop()
                region.append(cur)
                for q in board.neighbors(cur):
                    v = board.get(q)
                    if v == EMPTY:
                        if q not in visited:
                            visited.add(q)
                            stack.append(q)
                    else:
                        borders.add(v)
            if borders == {BLACK}:
                black_area += len(region)
            elif borders == {WHITE}:
                white_area += len(region)
            # else: neutral, counts for nobody

    return black_area, white_area

def determine_winner(board: Board, komi: float):
    """Return (winner_color_or_None, black_score, white_score_with_komi)."""
    b, w = area_score(board)
    w += komi
    if b > w:
        return BLACK, b, w
    if w > b:
        return WHITE, b, w
    return None, b, w  # exact tie (practically impossible with .5 komi)