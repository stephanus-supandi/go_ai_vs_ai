import unittest

from game.board import BLACK, EMPTY, WHITE, Board
from game.game_state import GameState
from game.rules import IllegalMoveError

# Classic ko shape on a 5x5 board:
#     col:  0 1 2 3
#   row 0:  . B W .
#   row 1:  B W . W     <- white (1,1) is in atari at (1,2)
#   row 2:  . B W .
KO_BLACK = [(0, 1), (1, 0), (2, 1)]
KO_WHITE = [(0, 2), (1, 1), (2, 2), (1, 3)]

def ko_state(to_play=BLACK):
    return GameState(size=5,
                     board=Board.from_lists(5, KO_BLACK, KO_WHITE),
                     to_play=to_play)

class KoTest(unittest.TestCase):
    def test_capture_sets_ko_point(self):
        st = ko_state()
        st.play((1, 2))                 # Black captures white (1,1)
        self.assertEqual(st.board.get((1, 1)), EMPTY)
        self.assertEqual(st.captures[BLACK], 1)
        self.assertEqual(st.ko_point, (1, 1))

    def test_immediate_recapture_is_forbidden(self):
        st = ko_state()
        st.play((1, 2))                 # Black takes the ko
        self.assertFalse(st.is_legal((1, 1)))
        with self.assertRaises(IllegalMoveError):
            st.play((1, 1))             # White may not retake immediately

    def test_recapture_allowed_after_elsewhere_moves(self):
        st = ko_state()
        st.play((1, 2))                 # Black takes
        st.play((4, 4))                 # White plays elsewhere
        st.play((4, 0))                 # Black answers elsewhere
        self.assertTrue(st.is_legal((1, 1)))
        st.play((1, 1))                 # White retakes the ko
        self.assertEqual(st.board.get((1, 2)), EMPTY)
        self.assertEqual(st.ko_point, (1, 2))   # ko flips
        self.assertFalse(st.is_legal((1, 2)))   # Black can't retake at once

    def test_ko_point_cleared_by_unrelated_move(self):
        st = ko_state()
        st.play((1, 2))                 # sets ko at (1,1)
        self.assertEqual(st.ko_point, (1, 1))
        st.play((4, 4))                 # White elsewhere clears ko
        self.assertIsNone(st.ko_point)

    def test_pass_clears_ko_point(self):
        st = ko_state()
        st.play((1, 2))
        self.assertEqual(st.ko_point, (1, 1))
        st.pass_turn()
        self.assertIsNone(st.ko_point)

    def test_capturing_two_stones_is_not_ko(self):
        # Capturing more than one stone never sets a ko point.
        black = [(1, 0), (1, 1), (1, 4), (1, 5), (0, 2), (0, 3), (2, 2), (2, 3)]
        white = [(1, 2), (1, 3)]
        st = GameState(size=9, board=Board.from_lists(9, black, white),
                       to_play=BLACK)
        # White group (1,2),(1,3) has no liberty in this setup? give it one:
        # remove (0,3),(2,3) so the group's liberties are (0,3),(2,3).
        black2 = [(1, 0), (1, 1), (1, 4), (1, 5), (0, 2), (2, 2)]
        white2 = [(1, 2), (1, 3)]
        st = GameState(size=9, board=Board.from_lists(9, black2, white2),
                       to_play=WHITE)
        st.pass_turn()                  # White passes; Black to play
        st.play((0, 3))                 # reduce to one liberty ((2,3))
        st.pass_turn()
        captured = st.play((2, 3))      # capture TWO stones
        self.assertEqual(len(captured), 2)
        self.assertIsNone(st.ko_point)

if __name__ == "__main__":
    unittest.main()