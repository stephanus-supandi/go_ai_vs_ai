import unittest

from game.board import BLACK, EMPTY, WHITE, Board

class LibertyTest(unittest.TestCase):
    def test_single_stone_center_has_four_liberties(self):
        b = Board.from_lists(9, [(4, 4)], [])
        self.assertEqual(b.count_liberties((4, 4)), 4)

    def test_corner_has_two_liberties(self):
        b = Board.from_lists(9, [(0, 0)], [])
        self.assertEqual(b.count_liberties((0, 0)), 2)

    def test_edge_has_three_liberties(self):
        b = Board.from_lists(9, [(0, 4)], [])
        self.assertEqual(b.count_liberties((0, 4)), 3)

    def test_two_connected_stones_share_liberties(self):
        b = Board.from_lists(9, [(4, 4), (4, 5)], [])
        self.assertEqual(len(b.find_group((4, 4))), 2)
        self.assertEqual(b.count_liberties((4, 5)), 6)

    def test_diagonal_stones_are_not_connected(self):
        b = Board.from_lists(9, [(4, 4), (5, 5)], [])
        self.assertEqual(len(b.find_group((4, 4))), 1)
        self.assertEqual(b.count_liberties((4, 4)), 4)

    def test_liberties_reduced_by_enemy_neighbors(self):
        b = Board.from_lists(9, [(4, 4)], [(4, 5), (3, 4)])
        self.assertEqual(b.count_liberties((4, 4)), 2)

    def test_zero_liberties_group_detection(self):
        b = Board.from_lists(9, [(0, 0)], [(0, 1), (1, 0)])
        self.assertEqual(b.count_liberties((0, 0)), 0)

    def test_large_group_liberties(self):
        # 2x2 black block in the center of 9x9 -> 8 liberties
        blacks = [(4, 4), (4, 5), (5, 4), (5, 5)]
        b = Board.from_lists(9, blacks, [])
        self.assertEqual(len(b.find_group((5, 5))), 4)
        self.assertEqual(b.count_liberties((4, 4)), 8)

if __name__ == "__main__":
    unittest.main()