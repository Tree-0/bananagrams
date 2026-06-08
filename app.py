from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flask import Flask, jsonify, render_template, request

from board import Board, Point
from tile_bag import draw_random_rack, make_custom_rack


BoardFactory = Callable[[Any], Board]


def create_app(board_factory: BoardFactory = Board) -> Flask:
    app = Flask(__name__)
    game = {"board": board_factory(draw_random_rack())}

    def current_board() -> Board:
        return game["board"]

    def state_response(
        *,
        success: bool = True,
        message: str | None = None,
        status_code: int = 200,
    ):
        state = current_board().to_state()
        state["success"] = success
        if message:
            state["message"] = message
        return jsonify(state), status_code

    def request_json() -> dict:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object.")
        return payload

    def parse_point(payload: dict, name: str | None = None) -> Point:
        source = payload if name is None else payload.get(name)
        if not isinstance(source, dict):
            raise ValueError("Expected point coordinates.")

        try:
            return Point(int(source["x"]), int(source["y"]))
        except (KeyError, TypeError, ValueError):
            raise ValueError("Expected integer x and y coordinates.") from None

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/state")
    def api_state():
        return state_response()

    @app.post("/api/new")
    def api_new():
        try:
            payload = request_json()
            mode = payload.get("mode")

            if mode == "custom":
                rack = make_custom_rack(str(payload.get("letters", "")))
                game["board"] = board_factory(rack)
                return state_response(message="Started a custom game.")

            if mode == "random":
                game["board"] = board_factory(draw_random_rack())
                return state_response(message="Started a random 21-tile game.")

            raise ValueError("Mode must be custom or random.")
        except ValueError as error:
            return state_response(
                success=False,
                message=str(error),
                status_code=400,
            )

    @app.post("/api/place")
    def api_place():
        try:
            payload = request_json()
            point = parse_point(payload)
            char = str(payload.get("char", ""))
            overwrite = bool(payload.get("overwrite", False))

            if overwrite:
                current_board().place_or_overwrite_tile(char, point.x, point.y)
            else:
                current_board().place_tile(char, point.x, point.y)

            return state_response(message=f"Placed {char.upper()} at ({point.x}, {point.y}).")
        except ValueError as error:
            return state_response(
                success=False,
                message=str(error),
                status_code=400,
            )

    @app.post("/api/remove")
    def api_remove():
        try:
            payload = request_json()
            point = parse_point(payload)
            if not current_board().remove_letter(point.x, point.y):
                raise ValueError(f"No tile placed at ({point.x}, {point.y}).")
            return state_response(message=f"Removed tile at ({point.x}, {point.y}).")
        except ValueError as error:
            return state_response(
                success=False,
                message=str(error),
                status_code=400,
            )

    @app.post("/api/move")
    def api_move():
        try:
            payload = request_json()
            from_point = parse_point(payload, "from")
            to_point = parse_point(payload, "to")
            current_board().move_tile(from_point, to_point)
            return state_response(
                message=(
                    f"Moved tile from ({from_point.x}, {from_point.y}) "
                    f"to ({to_point.x}, {to_point.y})."
                )
            )
        except ValueError as error:
            return state_response(
                success=False,
                message=str(error),
                status_code=400,
            )

    return app
