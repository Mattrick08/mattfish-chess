import os
from flask import Flask, render_template, jsonify, request
import secrets
import time as time_module
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

# ========== MULTIPLAYER (polling-based, no websockets) ==========
rooms = {}  # room_code -> room state dict

ROOM_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous chars (no I,O,0,1)
ROOM_MAX_AGE_SECONDS = 6 * 60 * 60  # cleanup rooms older than 6 hours

def generate_room_code():
    for _ in range(50):
        code = "".join(secrets.choice(ROOM_CODE_CHARS) for _ in range(6))
        if code not in rooms:
            return code
    raise RuntimeError("Could not generate a unique room code")

def cleanup_old_rooms():
    now = time_module.time()
    stale = [c for c, r in rooms.items() if now - r["created_at"] > ROOM_MAX_AGE_SECONDS]
    for c in stale:
        del rooms[c]

def get_room_or_error(code):
    if code not in rooms:
        return None, (jsonify({"error": "Room not found."}), 404)
    return rooms[code], None

def color_for_token(room, token):
    for color in ("white", "black"):
        if room["tokens"][color] == token:
            return color
    return None

def check_and_apply_timeout(room):
    """If it's currently someone's turn and their clock has run out, end the game. Read+mutate."""
    if not room["started"] or room["game_over"] or room["last_move_time"] is None:
        return
    board = room["board"]
    mover_color = "white" if board.turn == chess.WHITE else "black"
    elapsed = time_module.time() - room["last_move_time"]
    remaining = room["clocks"][mover_color] - elapsed
    if remaining <= 0:
        room["clocks"][mover_color] = 0
        room["game_over"] = True
        room["result"] = "0-1" if mover_color == "white" else "1-0"
        room["game_over_reason"] = "timeout"

def live_clocks(room):
    """Clocks as they should currently display, without permanently mutating stored state."""
    clocks = dict(room["clocks"])
    if room["started"] and not room["game_over"] and room["last_move_time"] is not None:
        board = room["board"]
        mover_color = "white" if board.turn == chess.WHITE else "black"
        elapsed = time_module.time() - room["last_move_time"]
        clocks[mover_color] = max(0, clocks[mover_color] - elapsed)
    return clocks

def room_public_state(room, code):
    board = room["board"]
    return {
        "code": code,
        "fen": board.fen(),
        "white_name": room["names"]["white"],
        "black_name": room["names"]["black"],
        "white_connected": room["tokens"]["white"] is not None,
        "black_connected": room["tokens"]["black"] is not None,
        "clocks": live_clocks(room),
        "time_control": room["time_control"],
        "check": board.is_check(),
        "game_over": room["game_over"],
        "result": room["result"],
        "game_over_reason": room.get("game_over_reason"),
        "legal_moves": [str(m) for m in board.legal_moves] if not room["game_over"] else [],
        "started": room["started"],
        "last_move": room["last_move"],
        "chat": room["chat"][-50:],
        "draw_offer": room.get("draw_offer"),
        "undo_offer": room.get("undo_offer"),
        "rematch_votes": list(room.get("rematch_votes") or []),
    }

@app.route("/multiplayer")
def multiplayer_page():
    return render_template("multiplayer.html")

@app.route("/api/mp/create", methods=["POST"])
def mp_create():
    cleanup_old_rooms()
    data = request.get_json() or {}
    name = (data.get("name") or "Player 1")[:20]
    color_pref = data.get("color", "random")
    minutes = max(1, min(180, int(data.get("minutes", 10))))
    increment = max(0, min(60, int(data.get("increment", 0))))

    if color_pref not in ("white", "black"):
        color_pref = secrets.choice(["white", "black"])

    code = generate_room_code()
    seconds = minutes * 60
    token = secrets.token_hex(12)

    rooms[code] = {
        "board": chess.Board(),
        "tokens": {"white": None, "black": None},
        "names": {"white": None, "black": None},
        "time_control": {"minutes": minutes, "increment": increment},
        "clocks": {"white": float(seconds), "black": float(seconds)},
        "last_move_time": None,
        "started": False,
        "game_over": False,
        "result": None,
        "game_over_reason": None,
        "last_move": None,
        "chat": [],
        "draw_offer": None,
        "undo_offer": None,
        "rematch_votes": set(),
        "created_at": time_module.time(),
    }
    rooms[code]["tokens"][color_pref] = token
    rooms[code]["names"][color_pref] = name

    return jsonify({"code": code, "color": color_pref, "token": token})

@app.route("/api/mp/join", methods=["POST"])
def mp_join():
    data = request.get_json() or {}
    code = (data.get("code") or "").strip().upper()
    name = (data.get("name") or "Player 2")[:20]

    room, err = get_room_or_error(code)
    if err:
        return err

    # Rejoining with an existing token (e.g. page refresh) just re-confirms identity
    existing_color = None
    open_color = None
    for c in ("white", "black"):
        if room["tokens"][c] is None and open_color is None:
            open_color = c

    if open_color is None:
        return jsonify({"error": "This room is already full."}), 400

    token = secrets.token_hex(12)
    room["tokens"][open_color] = token
    room["names"][open_color] = name

    if room["tokens"]["white"] and room["tokens"]["black"]:
        room["started"] = True
        room["last_move_time"] = time_module.time()

    return jsonify({"color": open_color, "token": token, **room_public_state(room, code)})

@app.route("/api/mp/state/<code>")
def mp_state(code):
    code = code.strip().upper()
    room, err = get_room_or_error(code)
    if err:
        return err

    token = request.args.get("token", "")
    color = color_for_token(room, token)
    if not color:
        return jsonify({"error": "Invalid token for this room."}), 403

    check_and_apply_timeout(room)
    state = room_public_state(room, code)
    state["your_color"] = color
    return jsonify(state)

@app.route("/api/mp/move", methods=["POST"])
def mp_move():
    data = request.get_json() or {}
    code = (data.get("code") or "").strip().upper()
    token = data.get("token", "")
    move_uci = data.get("move")

    room, err = get_room_or_error(code)
    if err:
        return err

    color = color_for_token(room, token)
    if not color:
        return jsonify({"error": "Invalid token for this room."}), 403

    if not room["started"] or room["game_over"]:
        return jsonify({"error": "Game is not active."}), 400

    check_and_apply_timeout(room)
    if room["game_over"]:
        return jsonify(room_public_state(room, code))

    board = room["board"]
    mover_color = "white" if board.turn == chess.WHITE else "black"
    if color != mover_color:
        return jsonify({"error": "It is not your turn."}), 400

    # Commit the elapsed time against the mover's clock, then add increment
    now = time_module.time()
    if room["last_move_time"] is not None:
        elapsed = now - room["last_move_time"]
        room["clocks"][mover_color] = max(0, room["clocks"][mover_color] - elapsed)
    room["last_move_time"] = now
    if room["clocks"][mover_color] <= 0:
        room["clocks"][mover_color] = 0
        room["game_over"] = True
        room["result"] = "0-1" if mover_color == "white" else "1-0"
        room["game_over_reason"] = "timeout"
        return jsonify(room_public_state(room, code))
    room["clocks"][mover_color] += room["time_control"]["increment"]

    try:
        move = chess.Move.from_uci(move_uci)
        if move not in board.legal_moves:
            return jsonify({"error": "Illegal move."}), 400
        board.push(move)
    except Exception:
        return jsonify({"error": "Invalid move format."}), 400

    room["last_move"] = move_uci
    room["draw_offer"] = None  # moving cancels any pending draw offer
    room["undo_offer"] = None  # moving cancels any pending undo request

    if board.is_game_over():
        room["game_over"] = True
        room["result"] = board.result()
        room["game_over_reason"] = "normal"

    return jsonify(room_public_state(room, code))

@app.route("/api/mp/resign", methods=["POST"])
def mp_resign():
    data = request.get_json() or {}
    code = (data.get("code") or "").strip().upper()
    token = data.get("token", "")

    room, err = get_room_or_error(code)
    if err:
        return err

    color = color_for_token(room, token)
    if not color:
        return jsonify({"error": "Invalid token for this room."}), 403

    if not room["game_over"]:
        room["game_over"] = True
        room["result"] = "0-1" if color == "white" else "1-0"
        room["game_over_reason"] = "resignation"

    return jsonify(room_public_state(room, code))

@app.route("/api/mp/undo", methods=["POST"])
def mp_undo():
    data = request.get_json() or {}
    code = (data.get("code") or "").strip().upper()
    token = data.get("token", "")
    action = data.get("action", "request")  # "request" or "respond"
    accept = data.get("accept", False)

    room, err = get_room_or_error(code)
    if err:
        return err

    color = color_for_token(room, token)
    if not color:
        return jsonify({"error": "Invalid token."}), 403

    if not room["started"] or room["game_over"]:
        return jsonify({"error": "Game is not active."}), 400

    board = room["board"]

    if action == "request":
        if len(board.move_stack) == 0:
            return jsonify({"error": "No moves to undo."}), 400
        room["undo_offer"] = color
        return jsonify(room_public_state(room, code))

    if action == "respond":
        if room["undo_offer"] is None or room["undo_offer"] == color:
            return jsonify({"error": "No undo request to respond to."}), 400
        if accept:
            # Pop 2 half-moves so the requesting player gets to move again;
            # if only 1 move was played, pop just that one
            pops = 2 if len(board.move_stack) >= 2 else 1
            for _ in range(pops):
                if board.move_stack:
                    board.pop()
            room["last_move"] = board.move_stack[-1].uci() if board.move_stack else None
            room["undo_offer"] = None
            return jsonify(room_public_state(room, code))
        else:
            room["undo_offer"] = None
            return jsonify(room_public_state(room, code))

    return jsonify({"error": "Unknown action."}), 400


@app.route("/api/mp/pgn/<code>")
def mp_pgn(code):
    code = code.strip().upper()
    room, err = get_room_or_error(code)
    if err:
        return err

    board = room["board"]
    white_name = room["names"].get("white") or "White"
    black_name = room["names"].get("black") or "Black"

    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = "MattFish Multiplayer"
    pgn_game.headers["Site"] = "MattFish"
    pgn_game.headers["White"] = white_name
    pgn_game.headers["Black"] = black_name
    pgn_game.headers["Result"] = board.result() if board.is_game_over() else "*"

    node = pgn_game
    for move in board.move_stack:
        node = node.add_variation(move)

    return jsonify({"pgn": str(pgn_game)})


@app.route("/api/mp/history/<code>")
def mp_history(code):
    code = code.strip().upper()
    room, err = get_room_or_error(code)
    if err:
        return err

    board = room["board"]
    moves = list(board.move_stack)

    replay = chess.Board()
    history = []
    for ply, move in enumerate(moves):
        white_to_move = replay.turn == chess.WHITE
        san = replay.san(move)
        replay.push(move)
        history.append({
            "ply": ply,
            "move_uci": move.uci(),
            "move_san": san,
            "fen": replay.fen(),
            "white_to_move_before": white_to_move,
        })

    return jsonify({
        "moves": history,
        "white_name": room["names"].get("white") or "White",
        "black_name": room["names"].get("black") or "Black",
        "result": board.result() if board.is_game_over() else "*",
    })


@app.route("/api/mp/rematch", methods=["POST"])
def mp_rematch():
    data = request.get_json() or {}
    code = (data.get("code") or "").strip().upper()
    token = data.get("token", "")

    room, err = get_room_or_error(code)
    if err:
        return err

    color = color_for_token(room, token)
    if not color:
        return jsonify({"error": "Invalid token."}), 403

    if not room["game_over"]:
        return jsonify({"error": "Game is not over yet."}), 400

    # Track who requested rematch; start as soon as both have accepted
    if "rematch_votes" not in room:
        room["rematch_votes"] = set()
    room["rematch_votes"].add(color)

    if len(room["rematch_votes"]) < 2:
        # Still waiting for the other player
        return jsonify({"waiting": True, "voted": color})

    # Both voted — swap colors and reset everything
    old_white_token = room["tokens"]["white"]
    old_black_token = room["tokens"]["black"]
    old_white_name  = room["names"]["white"]
    old_black_name  = room["names"]["black"]
    seconds = room["time_control"]["minutes"] * 60

    room["board"]            = chess.Board()
    room["tokens"]["white"]  = old_black_token
    room["tokens"]["black"]  = old_white_token
    room["names"]["white"]   = old_black_name
    room["names"]["black"]   = old_white_name
    room["clocks"]           = {"white": float(seconds), "black": float(seconds)}
    room["last_move_time"]   = time_module.time()
    room["started"]          = True
    room["game_over"]        = False
    room["result"]           = None
    room["game_over_reason"] = None
    room["last_move"]        = None
    room["draw_offer"]       = None
    room["undo_offer"]       = None
    room["rematch_votes"]    = set()

    state = room_public_state(room, code)
    # Tell each player their new color
    new_color = "white" if old_black_token == room["tokens"]["white"] else "black"
    state["your_new_color"] = "white" if color == "black" else "black"
    return jsonify(state)


@app.route("/api/mp/draw_offer", methods=["POST"])
def mp_draw_offer():
    data = request.get_json() or {}
    code = (data.get("code") or "").strip().upper()
    token = data.get("token", "")
    action = data.get("action", "offer")  # "offer" or "respond"
    accept = data.get("accept", False)

    room, err = get_room_or_error(code)
    if err:
        return err

    color = color_for_token(room, token)
    if not color:
        return jsonify({"error": "Invalid token."}), 403

    if not room["started"] or room["game_over"]:
        return jsonify({"error": "Game is not active."}), 400

    if action == "offer":
        room["draw_offer"] = color
        return jsonify(room_public_state(room, code))

    if action == "respond":
        if room["draw_offer"] is None or room["draw_offer"] == color:
            return jsonify({"error": "No draw offer to respond to."}), 400
        if accept:
            room["game_over"] = True
            room["result"] = "1/2-1/2"
            room["game_over_reason"] = "draw_agreement"
        room["draw_offer"] = None
        return jsonify(room_public_state(room, code))

    return jsonify({"error": "Unknown action."}), 400


@app.route("/api/mp/chat", methods=["POST"])
def mp_chat():
    data = request.get_json() or {}
    code = (data.get("code") or "").strip().upper()
    token = data.get("token", "")
    text = (data.get("text") or "").strip()[:300]

    room, err = get_room_or_error(code)
    if err:
        return err

    color = color_for_token(room, token)
    if not color or not text:
        return jsonify({"error": "Invalid request."}), 400

    room["chat"].append({
        "name": room["names"].get(color, "Player"),
        "text": text,
        "color": color,
        "ts": time_module.time(),
    })

    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(debug=False)
