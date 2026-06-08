from collections import Counter
import unittest
from unittest.mock import patch

from board import Board, Point, Tile, WILDCARD_CHAR


class FakeTrie:
    def __init__(self, words: set[str] | None = None):
        self.words = {word.upper() for word in words or set()}

    def search(self, word: str) -> bool:
        return word.upper() in self.words


class BoardTests(unittest.TestCase):
    def make_board(
        self,
        letters: str = "",
        valid_words: set[str] | None = None,
    ) -> Board:
        with patch(
            "board.trie_cache.load_or_build_trie",
            return_value=FakeTrie(valid_words),
        ):
            return Board(Counter(letters))

    def test_board_starts_with_unplaced_letters_and_empty_grid(self):
        board = self.make_board("BEE")

        self.assertEqual(board.unplaced_letters, Counter({"B": 1, "E": 2}))
        self.assertEqual(board.placed_tiles, {})

    def test_place_tile_records_tile_and_consumes_letter(self):
        board = self.make_board("BE")

        tile = board.place_tile("b", 2, 3)

        self.assertEqual(tile, Tile("B"))
        self.assertEqual(board.placed_tiles[Point(2, 3)], tile)
        self.assertEqual(board.unplaced_letters["B"], 0)

    def test_place_tile_marks_wildcards(self):
        board = self.make_board(WILDCARD_CHAR)

        tile = board.place_tile(WILDCARD_CHAR, 0, 0)

        self.assertEqual(tile, Tile(WILDCARD_CHAR, is_wildcard=True))

    def test_place_tile_rejects_unavailable_letters(self):
        board = self.make_board("A")

        with self.assertRaises(ValueError):
            board.place_tile("B", 0, 0)

    def test_place_tile_rejects_occupied_points_without_consuming_letter(self):
        board = self.make_board("BE")
        board.place_tile("B", 0, 0)

        with self.assertRaises(ValueError):
            board.place_tile("E", 0, 0)

        self.assertEqual(board.placed_tiles[Point(0, 0)], Tile("B"))
        self.assertEqual(board.unplaced_letters["E"], 1)

    def test_place_tile_maybe_returns_none_for_invalid_placement(self):
        board = self.make_board("A")

        self.assertIsNone(board.place_tile_maybe("B", 0, 0))

    def test_remove_letter_removes_tile_and_restores_counter(self):
        board = self.make_board("A")
        board.place_tile("A", 0, 0)

        removed = board.remove_letter(0, 0)

        self.assertTrue(removed)
        self.assertNotIn(Point(0, 0), board.placed_tiles)
        self.assertEqual(board.unplaced_letters["A"], 1)

    def test_remove_letter_returns_false_when_point_is_empty(self):
        board = self.make_board("A")

        self.assertFalse(board.remove_letter(0, 0))

    def test_get_formed_words_finds_horizontal_and_vertical_words(self):
        board = self.make_board("BEAT")
        board.place_tile("B", 0, 0)
        board.place_tile("E", 1, 0)
        board.place_tile("A", 0, 1)
        board.place_tile("T", 0, 2)

        self.assertEqual(board.get_formed_words(), {"BE", "BAT"})

    def test_is_valid_board_requires_all_formed_words_to_be_valid(self):
        board = self.make_board("BEAT", valid_words={"BE", "BAT"})
        board.place_tile("B", 0, 0)
        board.place_tile("E", 1, 0)
        board.place_tile("A", 0, 1)
        board.place_tile("T", 0, 2)

        self.assertTrue(board.is_valid_board())

    def test_is_valid_board_rejects_invalid_formed_words(self):
        board = self.make_board("BX", valid_words={"BE"})
        board.place_tile("B", 0, 0)
        board.place_tile("X", 1, 0)

        self.assertFalse(board.is_valid_board())

    def test_is_valid_board_rejects_single_isolated_tiles(self):
        board = self.make_board("A", valid_words={"A"})
        board.place_tile("A", 0, 0)

        self.assertFalse(board.is_valid_board())

    def test_is_valid_board_rejects_tiles_that_are_not_in_any_word(self):
        board = self.make_board("BEX", valid_words={"BE"})
        board.place_tile("B", 0, 0)
        board.place_tile("E", 1, 0)
        board.place_tile("X", 10, 10)

        self.assertFalse(board.is_valid_board())

    def test_place_or_overwrite_tile_replaces_existing_tile_atomically(self):
        board = self.make_board("BE")
        board.place_tile("B", 0, 0)

        tile = board.place_or_overwrite_tile("E", 0, 0)

        self.assertEqual(tile, Tile("E"))
        self.assertEqual(board.placed_tiles[Point(0, 0)], Tile("E"))
        self.assertEqual(board.unplaced_letters["B"], 1)
        self.assertEqual(board.unplaced_letters["E"], 0)

    def test_place_or_overwrite_tile_failure_preserves_existing_tile(self):
        board = self.make_board("BE")
        board.place_tile("B", 0, 0)

        with self.assertRaises(ValueError):
            board.place_or_overwrite_tile("X", 0, 0)

        self.assertEqual(board.placed_tiles[Point(0, 0)], Tile("B"))
        self.assertEqual(board.unplaced_letters["B"], 0)
        self.assertEqual(board.unplaced_letters["E"], 1)
        self.assertEqual(board.unplaced_letters["X"], 0)

    def test_place_or_overwrite_tile_with_same_letter_is_noop(self):
        board = self.make_board("BB")
        board.place_tile("B", 0, 0)

        board.place_or_overwrite_tile("B", 0, 0)

        self.assertEqual(board.placed_tiles[Point(0, 0)], Tile("B"))
        self.assertEqual(board.unplaced_letters["B"], 1)

    def test_move_tile_moves_placed_tile_without_changing_rack(self):
        board = self.make_board("A")
        board.place_tile("A", 0, 0)

        moved = board.move_tile(Point(0, 0), Point(3, -2))

        self.assertEqual(moved, Tile("A"))
        self.assertNotIn(Point(0, 0), board.placed_tiles)
        self.assertEqual(board.placed_tiles[Point(3, -2)], Tile("A"))
        self.assertEqual(board.unplaced_letters["A"], 0)

    def test_move_tile_rejects_occupied_target(self):
        board = self.make_board("AB")
        board.place_tile("A", 0, 0)
        board.place_tile("B", 1, 0)

        with self.assertRaises(ValueError):
            board.move_tile(Point(0, 0), Point(1, 0))

        self.assertEqual(board.placed_tiles[Point(0, 0)], Tile("A"))
        self.assertEqual(board.placed_tiles[Point(1, 0)], Tile("B"))

    def test_get_formed_word_details_preserves_duplicate_word_paths(self):
        board = self.make_board("BEBE", valid_words={"BE", "BB", "EE"})
        board.place_tile("B", 0, 0)
        board.place_tile("E", 1, 0)
        board.place_tile("B", 0, 1)
        board.place_tile("E", 1, 1)

        details = board.get_formed_word_details()
        horizontal_be_words = [
            detail
            for detail in details
            if detail["word"] == "BE" and detail["direction"] == "horizontal"
        ]

        self.assertEqual(len(horizontal_be_words), 2)
        self.assertEqual(len(details), 4)

    def test_to_state_serializes_board_for_ui(self):
        board = self.make_board("BE", valid_words={"BE"})
        board.place_tile("B", 0, 0)
        board.place_tile("E", 1, 0)

        state = board.to_state()

        self.assertEqual(state["rack"], {})
        self.assertEqual(
            state["placed_tiles"],
            [
                {"x": 0, "y": 0, "char": "B", "is_wildcard": False},
                {"x": 1, "y": 0, "char": "E", "is_wildcard": False},
            ],
        )
        self.assertTrue(state["is_valid"])
        self.assertEqual(state["formed_words"][0]["word"], "BE")


if __name__ == "__main__":
    unittest.main()
