import unittest

from game.board import BLACK, EMPTY, WHITE, Board
from game.game_state import GameState

def state_with(size, black, white, to_play=BLACK):
    return GameState(size=size, board=Board.from_lists(size, black, white),
                     to_play=to_play)

class CaptureTest(unittest.TestCase):
    def test_single_stone_capture_in_corner(self):
        # White (0,0) has one liberty at (1,0); Black fills it.
        st = state_with(5, [(0, 1)], [(0, 0)], to_play=BLACK)
        captured = st.play((1, 0))
        self.assertEqual(captured, [(0, 0)])
        self.assertEqual(st.board.get((0, 0)), EMPTY)
        self.assertEqual(st.captures[BLACK], 1)

    def test_single_stone_capture_in_center(self):
        st = state_with(9, [(3, 4), (4, 3), (5, 4)], [(4, 4)], to_play=BLACK)
        captured = st.play((4, 5))
        self.assertEqual(len(captured), 1)
        self.assertEqual(st.board.get((4, 4)), EMPTY)

    def test_multi_stone_capture_on_edge(self):
        # White (0,0),(0,1) with last liberty (0,2).
        st = state_with(5, [(1, 0), (1, 1)], [(0, 0), (0, 1)], to_play=BLACK)
        captured = st.play((0, 2))
        self.assertEqual(len(captured), 2)
        self.assertEqual(st.captures[BLACK], 2)
        self.assertEqual(st.board.get((0, 0)), EMPTY)
        self.assertEqual(st.board.get((0, 1)), EMPTY)

    def test_capture_two_separate_groups_with_one_move(self):
        # White singles at (1,1) and (1,3), both in atari; Black plays (1,2).
        black = [(0, 1), (1, 0), (2, 1), (0, 3), (1, 4), (2, 3)]
        white = [(1, 1), (1, 3)]
        st = state_with(5, black, white, to_play=BLACK)
        captured = st.play((1, 2))
        self.assertEqual(len(captured), 2)
        self.assertEqual(st.captures[BLACK], 2)

    def test_move_legal_only_because_it_captures(self):
        # (0,0) would be suicide, but it captures two atari white stones.
        black = [(0, 2), (1, 1), (2, 0)]
        white = [(0, 1), (1, 0)]
        st = state_with(5, black, white, to_play=BLACK)
        self.assertTrue(st.is_legal((0, 0)))
        captured = st.play((0, 0))
        self.assertEqual(len(captured), 2)
        # the black stone now has liberties where the white stones were
        self.assertEqual(st.board.count_liberties((0, 0)), 2)

    def test_capture_counts_per_color(self):
        st = state_with(5, [(0, 1)], [(0, 0)], to_play=BLACK)
        st.play((1, 0))                      # Black captures 1
        self.assertEqual(st.captures, {BLACK: 1, WHITE: 0})
        self.assertEqual(st.to_play, WHITE)

    def test_no_self_capture_of_own_group(self):
        # Filling a liberty of your OWN living group is fine (not a capture).
        st = state_with(5, [(2, 1), (2, 3), (1, 2)], [], to_play=BLACK)
        st.play((3, 2))
        self.assertEqual(st.captures[BLACK], 0)

if __name__ == "__main__":
    unittest.main()