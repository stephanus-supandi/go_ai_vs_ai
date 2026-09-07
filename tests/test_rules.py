import unittest

from game.board import BLACK, EMPTY, WHITE, Board
from game.game_state import GameOverError, GameState
from game.rules import IllegalMoveError
from game.scoring import area_score, determine_winner


def state_with(size, black, white, to_play=BLACK, komi=7.5):
    return GameState(size=size, board=Board.from_lists(size, black, white),
                     to_play=to_play, komi=komi)


class SuicideTest(unittest.TestCase):
    def test_suicide_in_corner_is_illegal(self):
        st = state_with(9, [(0, 1), (1, 0)], [], to_play=WHITE)
        self.assertFalse(st.is_legal((0, 0)))
        with self.assertRaises(IllegalMoveError):
            st.play((0, 0))

    def test_suicide_surrounded_point_is_illegal(self):
        black = [(1, 2), (2, 1), (2, 3), (3, 2)]
        st = state_with(9, black, [], to_play=WHITE)
        self.assertFalse(st.is_legal((2, 2)))

    def test_connecting_to_live_group_is_not_suicide(self):
        # white plays next to its own living group inside black's area.
        black = [(0, 1), (1, 0)]
        white = [(0, 2), (1, 2), (2, 2)]
        st = state_with(9, black, white, to_play=WHITE)
        self.assertTrue(st.is_legal((1, 1)))
        # (1,1) neighbors: (0,1)B,(1,0)B,(1,2)W,(2,1)empty -> liberty (2,1)
        st.play((1, 1))
        self.assertEqual(st.board.get((1, 1)), WHITE)


class OccupiedAndBoundsTest(unittest.TestCase):
    def test_occupied_point_is_illegal(self):
        st = state_with(9, [(4, 4)], [], to_play=WHITE)
        self.assertFalse(st.is_legal((4, 4)))

    def test_off_board_is_illegal(self):
        st = state_with(9, [], [])
        self.assertFalse(st.is_legal((-1, 0)))
        self.assertFalse(st.is_legal((0, 9)))

    def test_legal_moves_are_all_points_on_empty_board(self):
        st = state_with(5, [], [])
        self.assertEqual(len(st.legal_moves()), 25)


class TurnAndPassTest(unittest.TestCase):
    def test_turn_alternates(self):
        st = state_with(9, [], [])
        self.assertEqual(st.to_play, BLACK)
        st.play((4, 4))
        self.assertEqual(st.to_play, WHITE)
        st.play((2, 2))
        self.assertEqual(st.to_play, BLACK)

    def test_single_pass_does_not_end_game(self):
        st = state_with(9, [], [])
        st.pass_turn()
        self.assertFalse(st.game_over)
        self.assertEqual(st.consecutive_passes, 1)
        self.assertEqual(st.move_number, 1)
        self.assertEqual(st.to_play, WHITE)

    def test_consecutive_passes_end_game(self):
        st = state_with(9, [], [])
        st.pass_turn()
        st.pass_turn()
        self.assertTrue(st.game_over)
        with self.assertRaises(GameOverError):
            st.play((4, 4))

    def test_stone_after_pass_resets_consecutive_counter(self):
        st = state_with(9, [], [])
        st.pass_turn()
        st.play((4, 4))
        self.assertEqual(st.consecutive_passes, 0)
        self.assertFalse(st.game_over)

    def test_resign_ends_game_with_opponent_winner(self):
        st = state_with(9, [], [])
        st.resign()  # Black resigns on its own turn
        self.assertTrue(st.game_over)
        self.assertEqual(st.resigned_by, BLACK)
        self.assertEqual(st.winner(), WHITE)
        self.assertEqual(st.result_string(), "W+R")


class ResetTest(unittest.TestCase):
    def test_fresh_state_is_a_full_reset(self):
        st = state_with(9, [(4, 4)], [(2, 2)])
        st.play((3, 3))
        fresh = GameState(size=9)
        self.assertTrue(all(v == EMPTY
                            for row in fresh.board.grid for v in row))
        self.assertEqual(fresh.move_number, 0)
        self.assertEqual(fresh.captures, {BLACK: 0, WHITE: 0})
        self.assertIsNone(fresh.ko_point)
        self.assertFalse(fresh.game_over)
        self.assertEqual(fresh.to_play, BLACK)

    def test_clone_is_independent(self):
        st = state_with(9, [], [])
        clone = st.clone()
        clone.play((4, 4))
        self.assertEqual(st.board.get((4, 4)), EMPTY)   # original untouched
        self.assertEqual(clone.board.get((4, 4)), BLACK)
        self.assertEqual(st.move_number, 0)
        self.assertEqual(clone.move_number, 1)


class ScoringTest(unittest.TestCase):
    def test_area_score_partitions_the_board(self):
        # 9x9: black wall on col 4, white wall on col 6.
        black = [(r, 4) for r in range(9)]
        white = [(r, 6) for r in range(9)]
        b = Board.from_lists(9, black, white)
        ba, wa = area_score(b)
        # left region cols 0-3 (36 pts) + 9 stones = 45 black
        # col 5 is neutral (borders both), cols 7-8 (18) + 9 stones = 27 white
        self.assertEqual((ba, wa), (45, 27))

    def test_komi_decides_close_game(self):
        # Adjacent walls: black col 4, white col 5.
        # Empty cols 0-3 (36 pts) border black only -> black territory.
        # Empty cols 6-8 (27 pts) border white only -> white territory.
        # Black  = 9 stones + 36 = 45.
        # White  = 9 stones + 27 = 36, plus komi 7.5 = 43.5.
        black = [(r, 4) for r in range(9)]
        white = [(r, 5) for r in range(9)]
        b = Board.from_lists(9, black, white)
        winner, bs, ws = determine_winner(b, komi=7.5)
        self.assertEqual(bs, 45)
        self.assertEqual(ws, 43.5)
        self.assertEqual(winner, BLACK)

    def test_double_pass_game_is_scored(self):
        black = [(r, 4) for r in range(9)]
        white = [(r, 6) for r in range(9)]
        st = state_with(9, black, white, to_play=BLACK)
        st.pass_turn()
        st.pass_turn()
        self.assertTrue(st.game_over)
        self.assertEqual(st.winner(), BLACK)     # 45 vs 27+7.5
        self.assertTrue(st.result_string().startswith("B+"))


if __name__ == "__main__":
    unittest.main()
