"""Integration tests for the AI layer (MCTS and Random).

Behavioural tests only:
  * fail-fast turn validation (ValueError) for both AIs
  * full GameState immutability under MCTS search
  * legality of every move returned by MCTS
  * determinism for identical seed / position / parameters
  * consecutive passes terminate via the normal GameState path
  * MCTS vs MCTS / MCTS vs Random MUST reach game_over
  * Random vs Random MUST complete safely (either game_over or hit safety cap)

Illegal moves are never converted to passes here: play_full_game()
calls state.play() directly, so any IllegalMoveError fails the test.
"""
import unittest

from ai.mcts import MCTSAI
from ai.random_ai import RandomAI
from game.board import BLACK, WHITE, Board
from game.game_state import GameState

MOVE_CAP = 400   # safety cap for potentially cycling Random-vs-Random games


def play_full_game(black_ai, white_ai, size=5):
    """Play a complete game and return the finished GameState.

    Any illegal move returned by an AI raises IllegalMoveError from
    state.play() and fails the test (no silent pass conversion).
    """
    state = GameState(size=size, komi=5.5)
    while not state.game_over and state.move_number < MOVE_CAP:
        ai = black_ai if state.to_play == BLACK else white_ai
        move = ai.choose_move(state)
        if move is None:
            state.pass_turn()
        else:
            state.play(move)
    return state


class WrongTurnValidationTest(unittest.TestCase):
    def test_mcts_wrong_turn_raises_value_error(self):
        st = GameState(size=5, to_play=WHITE)
        ai = MCTSAI(BLACK, iterations=5, seed=1)
        with self.assertRaises(ValueError):
            ai.choose_move(st)

    def test_random_ai_wrong_turn_raises_value_error(self):
        st = GameState(size=5, to_play=WHITE)
        ai = RandomAI(BLACK, seed=1)
        with self.assertRaises(ValueError):
            ai.choose_move(st)


class MCTSImmutabilityTest(unittest.TestCase):
    def test_choose_move_does_not_mutate_state(self):
        st = GameState(size=5, komi=5.5,
                       board=Board.from_lists(5, [(2, 2), (3, 3)], [(1, 1)]),
                       to_play=BLACK)
        grid_before = [row[:] for row in st.board.grid]
        to_play_before = st.to_play
        history_before = list(st.move_history)
        captures_before = dict(st.captures)
        ko_before = st.ko_point
        passes_before = st.consecutive_passes
        resigned_before = st.resigned_by
        over_before = st.game_over

        ai = MCTSAI(BLACK, iterations=20, seed=42)
        ai.choose_move(st)

        self.assertEqual([row[:] for row in st.board.grid], grid_before)
        self.assertEqual(st.to_play, to_play_before)
        self.assertEqual(list(st.move_history), history_before)
        self.assertEqual(dict(st.captures), captures_before)
        self.assertEqual(st.ko_point, ko_before)
        self.assertEqual(st.consecutive_passes, passes_before)
        self.assertEqual(st.resigned_by, resigned_before)
        self.assertEqual(st.game_over, over_before)


class MCTSLegalityAndDeterminismTest(unittest.TestCase):
    def test_returned_move_is_legal(self):
        st = GameState(size=5, komi=5.5)
        ai = MCTSAI(BLACK, iterations=20, seed=7)
        move = ai.choose_move(st)
        if move is not None:
            self.assertTrue(st.is_legal(move))

    def test_same_seed_same_position_same_move(self):
        st = GameState(size=5, komi=5.5,
                       board=Board.from_lists(5, [(2, 2)], [(3, 3)]),
                       to_play=BLACK)
        ai1 = MCTSAI(BLACK, iterations=20, exploration=1.4142, seed=99)
        ai2 = MCTSAI(BLACK, iterations=20, exploration=1.4142, seed=99)
        self.assertEqual(ai1.choose_move(st), ai2.choose_move(st))


class TerminationTest(unittest.TestCase):
    def test_consecutive_passes_terminate_game(self):
        st = GameState(size=5, komi=5.5)
        st.play((2, 2))
        st.pass_turn()
        self.assertFalse(st.game_over)
        self.assertEqual(st.consecutive_passes, 1)
        st.pass_turn()
        self.assertTrue(st.game_over)
        self.assertEqual(st.consecutive_passes, 2)


class FullGameIntegrationTest(unittest.TestCase):
    def test_random_vs_random_completes_safely(self):
        final = play_full_game(
            RandomAI(BLACK, seed=11),
            RandomAI(WHITE, seed=12),
        )
        self.assertTrue(
            final.game_over or final.move_number == MOVE_CAP
        )
        self.assertLessEqual(final.move_number, MOVE_CAP)








    def test_mcts_vs_random_reaches_game_over(self):
        final = play_full_game(MCTSAI(BLACK, iterations=10, seed=13),
                               RandomAI(WHITE, seed=14))
        self.assertTrue(final.game_over)

    def test_random_vs_mcts_reaches_game_over(self):
        final = play_full_game(RandomAI(BLACK, seed=15),
                               MCTSAI(WHITE, iterations=10, seed=16))
        self.assertTrue(final.game_over)

    def test_mcts_vs_mcts_reaches_game_over(self):
        final = play_full_game(MCTSAI(BLACK, iterations=10, seed=17),
                               MCTSAI(WHITE, iterations=10, seed=18))
        self.assertTrue(final.game_over)


if __name__ == "__main__":
    unittest.main()
