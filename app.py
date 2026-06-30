import os
from flask import Flask, render_template, jsonify, request
import secrets
import chess
from engine import search as local_search, evaluate as static_eval
import requests
import chess.pgn
import io
from collections import defaultdict

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ========== CHESS GAME (vs Engine) ==========
games = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/play")
def play():
    return render_template("chess.html")

@app.route("/api/chess/new", methods=["POST"])
def new_chess_game():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    if not session_id:
        session_id = secrets.token_hex(16)
    player_color = data.get("color", "white")

    board = chess.Board()
    games[session_id] = {
        "board": board,
        "color": player_color
    }

    return jsonify({
        "fen": board.fen(),
        "legal_moves": [str(m) for m in board.legal_moves],
        "game_over": False,
        "check": False,
        "session_id": session_id
    })

@app.route("/api/chess/eval", methods=["POST"])
def chess_eval():
    data = request.get_json() or {}
    session_id = data.get("session_id")

    if not session_id or session_id not in games:
        return jsonify({"error": "No game found"}), 400

    game_data = games[session_id]
    board = game_data["board"]

    if board.is_game_over():
        if board.is_checkmate():
            if board.turn == chess.WHITE:
                return jsonify({"eval": -9999, "mate": -1})
            else:
                return jsonify({"eval": 9999, "mate": 1})
        return jsonify({"eval": 0, "mate": 0})

    score, _ = local_search(board, 3, time_limit=1.0)
    if board.turn == chess.BLACK:
        score = -score

    if abs(score) > 90000:
        mate_in = (99999 - abs(score)) // 2 + 1
        if score > 0:
            return jsonify({"eval": None, "mate": mate_in})
        else:
            return jsonify({"eval": None, "mate": -mate_in})

    return jsonify({"eval": score, "mate": 0})

def get_engine_move(board, difficulty):
    depth_map = {"Easy": 3, "Medium": 5, "Hard": 8}
    time_limit_map = {"Easy": 1.0, "Medium": 3.0, "Hard": 8.0}
    depth = depth_map.get(difficulty, 5)

    _, engine_move = local_search(board, depth, time_limit=time_limit_map.get(difficulty, 3.0))
    return engine_move

@app.route("/api/chess/move", methods=["POST"])
def chess_move():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "No session ID provided"}), 400
    player_move = data.get("move")
    difficulty = data.get("difficulty", "Medium")

    if session_id not in games:
        return jsonify({"error": "No game found"}), 400

    game_data = games[session_id]
    board = game_data["board"]
    player_color = game_data.get("color", "white")

    if player_move == "engine":
        if board.turn == chess.WHITE:
            engine_move = get_engine_move(board, difficulty)
            if engine_move:
                board.push(engine_move)

            game_over = board.is_game_over()
            return jsonify({
                "fen": board.fen(),
                "player_move": None,
                "engine_move": str(engine_move) if engine_move else None,
                "game_over": game_over,
                "result": board.result() if game_over else None,
                "legal_moves": [str(m) for m in board.legal_moves] if not game_over else [],
                "check": board.is_check()
            })

    if not player_move:
        return jsonify({"error": "No move provided"}), 400

    try:
        move = chess.Move.from_uci(player_move)
        if move not in board.legal_moves:
            return jsonify({"error": "Illegal move", "fen": board.fen(), "check": board.is_check()}), 400
        board.push(move)
    except Exception as e:
        return jsonify({"error": str(e), "fen": board.fen(), "check": board.is_check()}), 400

    if board.is_game_over():
        return jsonify({
            "fen": board.fen(),
            "player_move": player_move,
            "engine_move": None,
            "game_over": True,
            "result": board.result(),
            "legal_moves": [],
            "check": False
        })

    engine_move = None
    if (player_color == "white" and board.turn == chess.BLACK) or (player_color == "black" and board.turn == chess.WHITE):
        engine_move = get_engine_move(board, difficulty)
        if engine_move:
            board.push(engine_move)

    game_over = board.is_game_over()

    return jsonify({
        "fen": board.fen(),
        "player_move": player_move,
        "engine_move": str(engine_move) if engine_move else None,
        "game_over": game_over,
        "result": board.result() if game_over else None,
        "legal_moves": [str(m) for m in board.legal_moves] if not game_over else [],
        "check": board.is_check()
    })

@app.route("/api/chess/undo", methods=["POST"])
def chess_undo():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    if not session_id or session_id not in games:
        return jsonify({"error": "No game found"}), 400

    game_data = games[session_id]
    board = game_data["board"]

    if len(board.move_stack) >= 2:
        board.pop()
        board.pop()
    elif len(board.move_stack) == 1:
        board.pop()

    return jsonify({
        "fen": board.fen(),
        "legal_moves": [str(m) for m in board.legal_moves],
        "game_over": False,
        "check": board.is_check()
    })

@app.route("/api/chess/pgn/<session_id>")
def chess_pgn(session_id):
    if session_id not in games:
        return jsonify({"error": "No game found"}), 404

    game_data = games[session_id]
    board = game_data["board"]
    player_color = game_data.get("color", "white")

    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = "MattFish Chess Game"
    pgn_game.headers["Site"] = "MattFish"
    pgn_game.headers["White"] = "Player" if player_color == "white" else "MattFish Engine"
    pgn_game.headers["Black"] = "MattFish Engine" if player_color == "white" else "Player"
    pgn_game.headers["Result"] = board.result() if board.is_game_over() else "*"

    node = pgn_game
    for move in board.move_stack:
        node = node.add_variation(move)

    return jsonify({"pgn": str(pgn_game)})


@app.route("/api/chess/review/<session_id>")
def chess_review(session_id):
    if session_id not in games:
        return jsonify({"error": "No game found"}), 404

    game_data = games[session_id]
    final_board = game_data["board"]
    moves = list(final_board.move_stack)

    replay = chess.Board()
    history = []
    prev_eval = 0  # always from White's perspective, centipawns

    for ply, move in enumerate(moves):
        white_to_move = replay.turn == chess.WHITE
        san = replay.san(move)
        replay.push(move)

        if replay.is_checkmate():
            cur_eval = -99999 if white_to_move else 99999
        else:
            cur_eval = static_eval(replay)

        # "loss" = how much the position swung against the side that just moved
        if white_to_move:
            loss = prev_eval - cur_eval
        else:
            loss = cur_eval - prev_eval

        if abs(cur_eval) > 90000:
            classification = "Good"
        elif loss >= 250:
            classification = "Blunder"
        elif loss >= 100:
            classification = "Mistake"
        elif loss >= 50:
            classification = "Inaccuracy"
        else:
            classification = "Good"

        display_eval = max(-1000, min(1000, cur_eval)) if abs(cur_eval) <= 90000 else (1000 if cur_eval > 0 else -1000)

        history.append({
            "ply": ply,
            "move_uci": move.uci(),
            "move_san": san,
            "fen": replay.fen(),
            "white_to_move_before": white_to_move,
            "eval": display_eval,
            "mate": None if abs(cur_eval) <= 90000 else (1 if cur_eval > 0 else -1),
            "classification": classification
        })

        prev_eval = cur_eval

    return jsonify({
        "moves": history,
        "result": final_board.result() if final_board.is_game_over() else "*"
    })


# ========== CHESS.COM STATS ==========
headers = {"User-Agent": "Mozilla/5.0"}

@app.route("/stats/<username>")
def get_stats(username):
    url = f"https://api.chess.com/pub/player/{username}/stats"
    response = requests.get(url, headers=headers)
    data = response.json()

    profile_url = f"https://api.chess.com/pub/player/{username}"
    profile_response = requests.get(profile_url, headers=headers)
    profile_data = profile_response.json()
    avatar = profile_data.get("avatar", None)

    result = {}
    time_classes = {
        "Rapid": "chess_rapid",
        "Blitz": "chess_blitz",
        "Bullet": "chess_bullet"
    }

    for name, key in time_classes.items():
        section = data.get(key, {})
        if section:
            result[name] = {
                "current": section.get("last", {}).get("rating", "N/A"),
                "best": section.get("best", {}).get("rating", "N/A"),
                "wins": section.get("record", {}).get("win", 0),
                "draws": section.get("record", {}).get("draw", 0),
                "losses": section.get("record", {}).get("loss", 0),
            }

    return jsonify({"stats": result, "avatar": avatar})

@app.route("/history/<username>/<int:months>")
def get_history(username, months):
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    archives_response = requests.get(archives_url, headers=headers)
    archives_data = archives_response.json()
    archives = archives_data["archives"][-months:]

    rapid, blitz, bullet = [], [], []

    for archive in archives:
        games_response = requests.get(archive, headers=headers)
        games_data = games_response.json()

        for game in games_data["games"]:
            time_class = game.get("time_class")
            if game["white"]["username"].lower() == username.lower():
                rating = game["white"]["rating"]
            else:
                rating = game["black"]["rating"]

            if rating > 100:
                if time_class == "rapid":
                    rapid.append(rating)
                elif time_class == "blitz":
                    blitz.append(rating)
                elif time_class == "bullet":
                    bullet.append(rating)

    return jsonify({"rapid": rapid, "blitz": blitz, "bullet": bullet})

@app.route("/openings/<username>/<int:months>")
def get_openings(username, months):
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    archives_response = requests.get(archives_url, headers=headers)
    archives_data = archives_response.json()
    archives = archives_data["archives"][-months:]

    openings = defaultdict(lambda: {"wins": 0, "draws": 0, "losses": 0})

    for archive in archives:
        games_response = requests.get(archive, headers=headers)
        games_data = games_response.json()

        for game in games_data["games"]:
            pgn = game.get("pgn", "")
            if not pgn:
                continue

            pgn_io = io.StringIO(pgn)
            parsed_game = chess.pgn.read_game(pgn_io)
            if not parsed_game:
                continue

            opening = parsed_game.headers.get("ECOUrl", "")
            if not opening:
                continue

            opening_name = opening.split("/")[-1].replace("-", " ").title()
            white = game["white"]["username"].lower()
            result = game["white"]["result"] if white == username.lower() else game["black"]["result"]

            if result == "win":
                openings[opening_name]["wins"] += 1
            elif result in ["drawn", "stalemate", "agreed", "repetition", "insufficient", "timevsinsufficient"]:
                openings[opening_name]["draws"] += 1
            else:
                openings[opening_name]["losses"] += 1

    openings_list = []
    for name, record in openings.items():
        total = record["wins"] + record["draws"] + record["losses"]
        winrate = (record["wins"] + record["draws"] * 0.5) / total * 100 if total > 0 else 0
        openings_list.append({
            "name": name,
            "wins": record["wins"],
            "draws": record["draws"],
            "losses": record["losses"],
            "total": total,
            "winrate": round(winrate, 1)
        })

    return jsonify(openings_list)

if __name__ == "__main__":
    app.run(debug=False)
