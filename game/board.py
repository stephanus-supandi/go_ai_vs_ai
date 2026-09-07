"""Board representation and low-level stone operations.

Pure data structure: no turn management, no ko policy, no suicide policy.
Those live in rules.py / game_state.py.
"""
from __future__ import annotations

EMPTY = 0
BLACK = 1
WHITE = 2


def other(color: int) -> int:
    """Return the opposite color."""
    if color == BLACK:
        return WHITE
    if color == WHITE:
        return BLACK
    raise ValueError(f"other() called with non-color value: {color!r}")


class Board:
    """A Go board: size x size grid of EMPTY / BLACK / WHITE."""

    __slots__ = ("size", "grid")

    def __init__(self, size: int = 19, grid=None):
        self.size = size
        self.grid = grid if grid is not None else [[EMPTY] * size for _ in range(size)]

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def from_lists(cls, size, black_points, white_points):
        """Build a board from explicit stone lists (mainly for tests/setup)."""
        b = cls(size)
        for p in black_points:
            b.grid[p[0]][p[1]] = BLACK
        for p in white_points:
            b.grid[p[0]][p[1]] = WHITE
        return b

    def clone(self) -> "Board":
        return Board(self.size, [row[:] for row in self.grid])

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    def on_board(self, point) -> bool:
        r, c = point
        return 0 <= r < self.size and 0 <= c < self.size

    def get(self, point) -> int:
        return self.grid[point[0]][point[1]]

    def neighbors(self, point):
        r, c = point
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            q = (r + dr, c + dc)
            if self.on_board(q):
                yield q

    def empty_points(self):
        pts = []
        g = self.grid
        for r in range(self.size):
            row = g[r]
            for c in range(self.size):
                if row[c] == EMPTY:
                    pts.append((r, c))
        return pts

    def find_group(self, point) -> set:
        """All stones orthogonally connected to `point` with the same color."""
        color = self.get(point)
        if color == EMPTY:
            raise ValueError("find_group() on an empty point")
        stack = [point]
        seen = {point}
        while stack:
            cur = stack.pop()
            for q in self.neighbors(cur):
                if q not in seen and self.get(q) == color:
                    seen.add(q)
                    stack.append(q)
        return seen

    def group_liberties(self, group) -> set:
        """Empty points adjacent to any stone of `group`."""
        libs = set()
        for stone in group:
            for q in self.neighbors(stone):
                if self.get(q) == EMPTY:
                    libs.add(q)
        return libs

    def count_liberties(self, point) -> int:
        return len(self.group_liberties(self.find_group(point)))

    # ------------------------------------------------------------------ #
    # Mutations (low-level; legality must be checked by caller)
    # ------------------------------------------------------------------ #
    def remove_group(self, group) -> None:
        for (r, c) in group:
            self.grid[r][c] = EMPTY

    def place_and_capture(self, point, color) -> list:
        """Place `color` at `point`, remove enemy groups with zero liberties.

        Returns the SORTED list of captured enemy points so callers and
        tests always see a deterministic order.
        """
        self.grid[point[0]][point[1]] = color
        enemy = other(color)
        captured = set()
        for q in self.neighbors(point):
            if self.get(q) == enemy and q not in captured:
                group = self.find_group(q)
                if not self.group_liberties(group):
                    self.remove_group(group)
                    captured |= group
        return sorted(captured)
