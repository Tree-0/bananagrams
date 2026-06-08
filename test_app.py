from collections import Counter
import unittest

from app import create_app
from board import Board
from test_board import FakeTrie


class AppTests(unittest.TestCase):
    def make_app(self):
        def board_factory(rack: Counter[str]) -> Board:
            board = Board(rack)
            board.valid_words = FakeTrie({"BE", "BEAN"})
            return board

        app = create_app(board_factory=board_factory)
        app.config.update(TESTING=True)
        return app

    def test_new_custom_game_returns_normalized_rack(self):
        client = self.make_app().test_client()

        response = client.post("/api/new", json={"mode": "custom", "letters": "bean"})
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["rack"], {"A": 1, "B": 1, "E": 1, "N": 1})

    def test_new_random_game_returns_21_tiles(self):
        client = self.make_app().test_client()

        response = client.post("/api/new", json={"mode": "random"})
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(sum(data["rack"].values()), 21)

    def test_place_endpoint_places_tiles_and_reports_valid_words(self):
        client = self.make_app().test_client()
        client.post("/api/new", json={"mode": "custom", "letters": "BE"})

        client.post("/api/place", json={"x": 0, "y": 0, "char": "B"})
        response = client.post("/api/place", json={"x": 1, "y": 0, "char": "E"})
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["is_valid"])
        self.assertEqual(data["formed_words"][0]["word"], "BE")

    def test_place_endpoint_overwrites_when_available(self):
        client = self.make_app().test_client()
        client.post("/api/new", json={"mode": "custom", "letters": "BE"})
        client.post("/api/place", json={"x": 0, "y": 0, "char": "B"})

        response = client.post("/api/place", json={
            "x": 0,
            "y": 0,
            "char": "E",
            "overwrite": True,
        })
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["placed_tiles"], [
            {"x": 0, "y": 0, "char": "E", "is_wildcard": False},
        ])
        self.assertEqual(data["rack"], {"B": 1})

    def test_place_endpoint_rejects_unavailable_tile(self):
        client = self.make_app().test_client()
        client.post("/api/new", json={"mode": "custom", "letters": "B"})

        response = client.post("/api/place", json={"x": 0, "y": 0, "char": "X"})
        data = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertFalse(data["success"])
        self.assertEqual(data["placed_tiles"], [])

    def test_remove_endpoint_returns_tile_to_rack(self):
        client = self.make_app().test_client()
        client.post("/api/new", json={"mode": "custom", "letters": "B"})
        client.post("/api/place", json={"x": 0, "y": 0, "char": "B"})

        response = client.post("/api/remove", json={"x": 0, "y": 0})
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["rack"], {"B": 1})
        self.assertEqual(data["placed_tiles"], [])

    def test_move_endpoint_moves_tile_without_changing_rack(self):
        client = self.make_app().test_client()
        client.post("/api/new", json={"mode": "custom", "letters": "B"})
        client.post("/api/place", json={"x": 0, "y": 0, "char": "B"})

        response = client.post("/api/move", json={
            "from": {"x": 0, "y": 0},
            "to": {"x": 2, "y": -1},
        })
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["rack"], {})
        self.assertEqual(data["placed_tiles"], [
            {"x": 2, "y": -1, "char": "B", "is_wildcard": False},
        ])

    def test_move_endpoint_rejects_occupied_target(self):
        client = self.make_app().test_client()
        client.post("/api/new", json={"mode": "custom", "letters": "BE"})
        client.post("/api/place", json={"x": 0, "y": 0, "char": "B"})
        client.post("/api/place", json={"x": 1, "y": 0, "char": "E"})

        response = client.post("/api/move", json={
            "from": {"x": 0, "y": 0},
            "to": {"x": 1, "y": 0},
        })
        data = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertFalse(data["success"])
        self.assertEqual(len(data["placed_tiles"]), 2)


if __name__ == "__main__":
    unittest.main()
