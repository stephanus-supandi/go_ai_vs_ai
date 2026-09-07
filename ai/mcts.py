"""Monte Carlo Tree Search AI.

Four canonical phases:
  1. Selection    - UCT descent while children are fully expanded
  2. Expansion    - add one untried child (legal moves + pass)
  3. Simulation   - random rollout with a simple eye-filling avoidance
                    policy and a small pass bias, terminated by double
                    pass or a move cap; scored with area scoring
  4. Backprop     - update visits/wins up the tree; wins are stored from
                    the perspective of the player who moved INTO the node

Perspective model (do not invert):
  * node.state is the state AFTER node.move was played
  * node.player_just_moved is the color that played node.move
  * node.wins counts results from player_just_moved's perspective
  * at a node X the chooser is X.state.to_play; every child C of X has
    C.player_just_moved == X.state.to_play, so C.wins / C.visits is
    directly the chooser's win rate (no inversion in UCT)
  * backpropagation compares the rollout winner with player_just_moved

Deterministic when constructed with a seed. Pure Python - this is a
correct, clean baseline, NOT a fast engine.
"""
from __future__ import annotations

import math
import random as _random


class MCTSNode:
    __slots__ = ("state", "parent", "move", "player_just_moved",
                 "children", "untried", "visits", "wins")

    def __init__(self, state, parent=None, move=None, player_just_moved=None):
        self.state = state                    # GameState AFTER `move`
        self.parent = parent
        self.move = move                      # point, None (pass), or root
        self.player_just_moved = player_just_moved
        self.children = []
        self.untried = None                   # lazily built move list
        self.visits = 0
        self.wins = 0.0                       # from player_just_moved's POV

    def untried_moves(self, rng):
        if self.untried is None:
            if self.state.game_over:
                self.untried = []
            else:
                self.untried = self.state.legal_moves() + [None]  # None = pass
                rng.shuffle(self.untried)
        return self.untried


def _is_own_eye(board, point, color) -> bool:
    """Simple eye heuristic: all orthogonal neighbors are `color`."""
    for q in board.neighbors(point):
        if board.get(q) != color:
            return False
    return True


class MCTSAI:
    def __init__(self, color: int, iterations: int = 200,
                 exploration: float = 1.4142, seed=None,
                 pass_bias: float = 0.05, max_rollout_moves=None):
        self.color = color
        self.iterations = iterations
        self.exploration = exploration
        self.pass_bias = pass_bias
        self.max_rollout_moves = max_rollout_moves
        self.rng = _random.Random(seed)

    @property
    def name(self):
        return f"MCTS({self.iterations})"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def choose_move(self, state):
        """Return the chosen point, or None to pass.

        Fail-fast: raises ValueError when it is not this AI's turn,
        before any search is performed.  Never mutates the supplied
        state: the root and every rollout operate on clones only.
        """
        if state.to_play != self.color:
            raise ValueError(
                f"MCTSAI plays color {self.color} but state.to_play is "
                f"{state.to_play}"
            )
        if state.game_over:
            return None

        root = MCTSNode(state.clone())
        for _ in range(self.iterations):
            node = self._select(root)
            if not node.state.game_over and node.untried_moves(self.rng):
                node = self._expand(node)
            winner = self._rollout(node.state.clone())
            self._backpropagate(node, winner)

        if not root.children:
            return None
        # Most-visited child; deterministic random tie-break.
        best = max(root.children, key=lambda c: (c.visits, self.rng.random()))
        return best.move

    # ------------------------------------------------------------------ #
    # 1. Selection
    # ------------------------------------------------------------------ #
    def _select(self, node):
        while True:
            if node.state.game_over:
                return node
            if node.untried_moves(self.rng):
                return node
            if not node.children:
                return node
            node = self._best_uct_child(node)

    def _best_uct_child(self, node):
        log_parent = math.log(node.visits + 1)
        best, best_val = None, -1.0
        for child in node.children:
            exploit = child.wins / child.visits
            explore = self.exploration * math.sqrt(log_parent / child.visits)
            val = exploit + explore + self.rng.random() * 1e-9  # tie-break
            if val > best_val:
                best_val, best = val, child
        return best

    # ------------------------------------------------------------------ #
    # 2. Expansion
    # ------------------------------------------------------------------ #
    def _expand(self, node):
        untried = node.untried_moves(self.rng)
        move = untried.pop(self.rng.randrange(len(untried)))
        child_state = node.state.clone()
        player = node.state.to_play
        if move is None:
            child_state.pass_turn()
        else:
            child_state.play(move)
        child = MCTSNode(child_state, parent=node, move=move,
                         player_just_moved=player)
        node.children.append(child)
        return child

    # ------------------------------------------------------------------ #
    # 3. Simulation / rollout
    # ------------------------------------------------------------------ #
    def _rollout(self, state):
        rng = self.rng
        cap = self.max_rollout_moves or state.size * state.size
        plies = 0
        while not state.game_over and plies < cap:
            color = state.to_play
            board = state.board
            candidates = [p for p in state.legal_moves()
                          if not _is_own_eye(board, p, color)]
            bias_active = plies > board.size
            if not candidates or (bias_active and rng.random() < self.pass_bias):
                state.pass_turn()
            else:
                state.play(candidates[rng.randrange(len(candidates))])
            plies += 1
        return state.winner()  # None possible only for unfinished/tie

    # ------------------------------------------------------------------ #
    # 4. Backpropagation
    # ------------------------------------------------------------------ #
    def _backpropagate(self, node, winner):
        while node is not None:
            node.visits += 1
            p = node.player_just_moved
            if p is not None:
                if winner is None:
                    node.wins += 0.5
                elif winner == p:
                    node.wins += 1.0
            node = node.parent
