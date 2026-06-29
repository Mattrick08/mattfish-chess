import os
import secrets
import random
import string
from collections import defaultdict

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
import chess
import requests
import chess.pgn
import io

from engine import search as local_search

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ========== SOCKETIO SETUP ==========
# Use eventlet for WebSocket support on Render
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ========== IN-MEMORY STORES ==========
# Chess games vs engine (existing)
engine_games = {}

# Multiplayer rooms: room_code -> room_data
# room_data = {
#     "host_sid": str,
#     "guest_sid": str or None,
#     "spectator_sids": set(),
#     "board": chess.Board,
#     "white_sid": str,  # who plays white
#     "black_sid": str,  # who plays black
#     "chat_history": [],
#     "time_control": {"minutes": 10, "increment": 0},
#     "white_time": 600,
#     "black_time": 600,
#     "active_timer": None,  # 'white' or 'black'
#     "timer_started": False,
#     "game_started": False,
#     "game_over": False,
#     "result": None,
#     "move_history": [],
#     "last_move": None,
#     "draw_offered_by": None,
# }
mp_rooms = {}

# Map sid -> room_code for quick lookup
sid_to_room = {}

# ========== HELPER FUNCTIONS ==========

def generate_room_code(length=6):
    """Generate a unique 6-character room code."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if code not in mp_rooms:
            return code

def get_room_players(room_code):
    """Get player info for a room."""
    room = mp_rooms.get(room_code)
    if not room:
        return {}
    return {
        "white": room.get("white_sid"),
        "black": room.get("black_sid"),
        "host": room.get("host_sid"),
        "guest": room.get("guest_sid"),
    }

def get_player_color(room_code, sid):
    """Get which color a sid plays in a room."""
    room = mp_rooms.get(room_code)
    if not room:
        return None
    if room.get("white_sid") == sid:
        return "white"
    if room.get("black_sid") == sid:
        return "black"
    return None

def is_spectator(room_code, sid):
    """Check if sid is a spectator in the room."""
    room = mp_rooms.get(room_code)
    if not room:
        return False
    return sid in room.get("spectator_sids", set())

def format_time(seconds):
    """Format seconds to MM:SS."""
    if seconds <= 0:
        return "0:00"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"

# ========== ROUTES ==========

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/play")
def play():
    return render_template("chess.html")

@app.route("/play/<room_code>")
def play_room(room_code):
    """Direct link to join a room."""
    return render_template("chess.html", room_code=room_code)

# ========== ENGINE GAME API (EXISTING) ==========

@app.route("/api/chess/new", methods=["POST"])
def new_chess_game():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    if not session_id:
        session_id = secrets.token_hex(16)
    player_color = data.get("color", "white")

    board = chess.Board()
    engine_games[session_id] = {
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

    if not session_id or session_id not in engine_games:
        return jsonify({"error": "No game found"}), 400

    game_data = engine_games[session_id]
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

    if session_id not in engine_games:
        return jsonify({"error": "No game found"}), 400

    game_data = engine_games[session_id]
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
    if not session_id or session_id not in engine_games:
        return jsonify({"error": "No game found"}), 400

    game_data = engine_games[session_id]
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

# ========== CHESS.COM STATS (EXISTING) ==========
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


# ========== SOCKETIO EVENTS - MULTIPLAYER ==========

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    room_code = sid_to_room.get(sid)

    if room_code and room_code in mp_rooms:
        room = mp_rooms[room_code]

        # Remove from spectators
        if sid in room.get("spectator_sids", set()):
            room["spectator_sids"].discard(sid)

        # Handle player disconnect
        if sid == room.get("host_sid"):
            # Host left - notify guest and spectators, close room after delay
            socketio.emit('player_left', {
                'message': 'Host left the room.',
                'player': 'host'
            }, room=room_code)
            # Give 30 seconds for reconnection, then clean up
            # For now, keep room alive but mark host as gone
            room["host_sid"] = None
        elif sid == room.get("guest_sid"):
            room["guest_sid"] = None
            socketio.emit('player_left', {
                'message': 'Guest left the room.',
                'player': 'guest'
            }, room=room_code)

        # Clean up empty rooms
        if room.get("host_sid") is None and room.get("guest_sid") is None and len(room.get("spectator_sids", set())) == 0:
            del mp_rooms[room_code]

    if sid in sid_to_room:
        del sid_to_room[sid]

    print(f'Client disconnected: {sid}')


@socketio.on('create_room')
def handle_create_room(data):
    """Host creates a new room."""
    sid = request.sid
    time_control = data.get('time_control', {'minutes': 10, 'increment': 0})

    room_code = generate_room_code()

    # Host plays white by default
    board = chess.Board()
    total_time = time_control['minutes'] * 60

    mp_rooms[room_code] = {
        "host_sid": sid,
        "guest_sid": None,
        "spectator_sids": set(),
        "board": board,
        "white_sid": sid,
        "black_sid": None,
        "chat_history": [],
        "time_control": time_control,
        "white_time": total_time,
        "black_time": total_time,
        "active_timer": None,
        "timer_started": False,
        "game_started": False,
        "game_over": False,
        "result": None,
        "move_history": [],
        "last_move": None,
        "draw_offered_by": None,
    }

    sid_to_room[sid] = room_code
    join_room(room_code)

    emit('room_created', {
        'room_code': room_code,
        'your_color': 'white',
        'time_control': time_control,
        'message': 'Room created! Share this code with your friend.',
        'fen': board.fen(),
        'legal_moves': [str(m) for m in board.legal_moves]
    })

    print(f'Room {room_code} created by {sid}')


@socketio.on('join_room')
def handle_join_room(data):
    """Guest joins a room by code."""
    sid = request.sid
    room_code = data.get('room_code', '').upper().strip()
    mode = data.get('mode', 'play')  # 'play' or 'spectate'

    if not room_code or room_code not in mp_rooms:
        emit('join_error', {'message': 'Room not found. Check the code and try again.'})
        return

    room = mp_rooms[room_code]

    if mode == 'spectate':
        # Spectator joins
        room["spectator_sids"].add(sid)
        sid_to_room[sid] = room_code
        join_room(room_code)

        emit('joined_as_spectator', {
            'room_code': room_code,
            'message': f'You are now spectating room {room_code}.',
            'fen': room["board"].fen(),
            'move_history': room["move_history"],
            'white_time': room["white_time"],
            'black_time': room["black_time"],
            'chat_history': room["chat_history"],
            'game_started': room["game_started"],
            'game_over': room["game_over"],
            'result': room["result"],
            'players': {
                'white': room.get("white_sid") is not None,
                'black': room.get("black_sid") is not None
            }
        })

        # Notify others
        emit('spectator_joined', {
            'message': 'A spectator joined the room.'
        }, room=room_code, include_self=False)

        print(f'Spectator {sid} joined room {room_code}')
        return

    # Play mode
    if room["guest_sid"] is not None:
        emit('join_error', {'message': 'Room is full. You can spectate instead!'})
        return

    room["guest_sid"] = sid
    room["black_sid"] = sid
    sid_to_room[sid] = room_code
    join_room(room_code)

    emit('joined_room', {
        'room_code': room_code,
        'your_color': 'black',
        'message': f'Joined room {room_code}! Waiting for host to start...',
        'fen': room["board"].fen(),
        'legal_moves': [str(m) for m in room["board"].legal_moves],
        'time_control': room["time_control"],
        'opponent': 'Host'
    })

    # Notify host that guest joined
    emit('guest_joined', {
        'message': 'Your opponent has joined! Click Start Game when ready.',
        'guest_sid': sid
    }, room=room["host_sid"])

    print(f'Guest {sid} joined room {room_code}')


@socketio.on('start_game')
def handle_start_game(data):
    """Host starts the game."""
    sid = request.sid
    room_code = sid_to_room.get(sid)

    if not room_code or room_code not in mp_rooms:
        emit('error', {'message': 'Room not found.'})
        return

    room = mp_rooms[room_code]

    if sid != room["host_sid"]:
        emit('error', {'message': 'Only the host can start the game.'})
        return

    if room["guest_sid"] is None:
        emit('error', {'message': 'Waiting for opponent to join.'})
        return

    room["game_started"] = True
    room["timer_started"] = True
    room["active_timer"] = 'white'

    total_time = room["time_control"]["minutes"] * 60
    room["white_time"] = total_time
    room["black_time"] = total_time

    socketio.emit('game_started', {
        'message': 'Game started! White to move.',
        'white_time': room["white_time"],
        'black_time': room["black_time"],
        'fen': room["board"].fen(),
        'legal_moves': [str(m) for m in room["board"].legal_moves]
    }, room=room_code)

    print(f'Game started in room {room_code}')


@socketio.on('make_move')
def handle_make_move(data):
    """Player makes a move."""
    sid = request.sid
    room_code = sid_to_room.get(sid)

    if not room_code or room_code not in mp_rooms:
        emit('error', {'message': 'Not in a room.'})
        return

    room = mp_rooms[room_code]

    if not room["game_started"] or room["game_over"]:
        emit('error', {'message': 'Game not active.'})
        return

    move_uci = data.get('move')
    if not move_uci:
        emit('error', {'message': 'No move provided.'})
        return

    board = room["board"]

    # Check if it's this player's turn
    color = get_player_color(room_code, sid)
    if color is None:
        emit('error', {'message': 'You are not a player in this game.'})
        return

    expected_turn = 'white' if board.turn == chess.WHITE else 'black'
    if color != expected_turn:
        emit('error', {'message': 'Not your turn!'})
        return

    try:
        move = chess.Move.from_uci(move_uci)
        if move not in board.legal_moves:
            emit('error', {'message': 'Illegal move.'})
            return

        board.push(move)
    except Exception as e:
        emit('error', {'message': f'Invalid move: {str(e)}'})
        return

    # Add increment to the player who just moved
    inc = room["time_control"].get("increment", 0)
    if color == 'white':
        room["white_time"] += inc
    else:
        room["black_time"] += inc

    # Switch timer
    room["active_timer"] = 'black' if color == 'white' else 'white'

    # Record move
    move_notation = str(move)
    if color == 'white':
        room["move_history"].append({"white": move_notation, "black": None})
    else:
        if room["move_history"]:
            room["move_history"][-1]["black"] = move_notation

    room["last_move"] = {
        "from": move_uci[:2],
        "to": move_uci[2:4]
    }

    # Check game over
    game_over = board.is_game_over()
    result = None
    if game_over:
        room["game_over"] = True
        room["result"] = board.result()
        room["active_timer"] = None

    # Broadcast move to everyone in room
    socketio.emit('move_made', {
        'move': move_uci,
        'player': color,
        'fen': board.fen(),
        'legal_moves': [str(m) for m in board.legal_moves] if not game_over else [],
        'white_time': room["white_time"],
        'black_time': room["black_time"],
        'active_timer': room["active_timer"],
        'game_over': game_over,
        'result': result,
        'check': board.is_check(),
        'move_history': room["move_history"],
        'last_move': room["last_move"]
    }, room=room_code)

    print(f'Move {move_uci} by {color} in room {room_code}')


@socketio.on('send_chat')
def handle_chat(data):
    """Send a chat message."""
    sid = request.sid
    room_code = sid_to_room.get(sid)

    if not room_code or room_code not in mp_rooms:
        emit('error', {'message': 'Not in a room.'})
        return

    message = data.get('message', '').strip()
    if not message or len(message) > 500:
        emit('error', {'message': 'Message too long or empty.'})
        return

    room = mp_rooms[room_code]

    # Determine sender identity
    color = get_player_color(room_code, sid)
    if color:
        sender = f'{color.capitalize()} Player'
    elif is_spectator(room_code, sid):
        sender = 'Spectator'
    else:
        sender = 'Unknown'

    chat_entry = {
        'sender': sender,
        'message': message,
        'timestamp': int(time.time())
    }
    room["chat_history"].append(chat_entry)

    # Keep only last 100 messages
    if len(room["chat_history"]) > 100:
        room["chat_history"] = room["chat_history"][-100:]

    socketio.emit('chat_message', chat_entry, room=room_code)
    print(f'Chat in {room_code}: {sender}: {message}')


@socketio.on('offer_draw')
def handle_offer_draw(data):
    """Player offers a draw."""
    sid = request.sid
    room_code = sid_to_room.get(sid)

    if not room_code or room_code not in mp_rooms:
        return

    room = mp_rooms[room_code]
    color = get_player_color(room_code, sid)

    if not color or room["game_over"]:
        return

    room["draw_offered_by"] = color

    socketio.emit('draw_offered', {
        'offered_by': color,
        'message': f'{color.capitalize()} offers a draw. Accept?'
    }, room=room_code)


@socketio.on('respond_draw')
def handle_respond_draw(data):
    """Respond to draw offer."""
    sid = request.sid
    room_code = sid_to_room.get(sid)

    if not room_code or room_code not in mp_rooms:
        return

    room = mp_rooms[room_code]
    accepted = data.get('accepted', False)
    color = get_player_color(room_code, sid)

    if not color or room["draw_offered_by"] == color:
        return

    if accepted:
        room["game_over"] = True
        room["result"] = "1/2-1/2"
        room["active_timer"] = None

        socketio.emit('game_over', {
            'result': '1/2-1/2',
            'reason': 'Draw by agreement',
            'message': 'Game drawn by agreement!'
        }, room=room_code)
    else:
        room["draw_offered_by"] = None
        socketio.emit('draw_declined', {
            'message': 'Draw offer declined.'
        }, room=room_code)


@socketio.on('resign')
def handle_resign(data):
    """Player resigns."""
    sid = request.sid
    room_code = sid_to_room.get(sid)

    if not room_code or room_code not in mp_rooms:
        return

    room = mp_rooms[room_code]
    color = get_player_color(room_code, sid)

    if not color or room["game_over"]:
        return

    room["game_over"] = True
    room["active_timer"] = None

    if color == 'white':
        room["result"] = "0-1"
    else:
        room["result"] = "1-0"

    socketio.emit('game_over', {
        'result': room["result"],
        'reason': f'{color.capitalize()} resigned',
        'message': f'{color.capitalize()} resigned! Game over.'
    }, room=room_code)


@socketio.on('request_timer_sync')
def handle_timer_sync(data):
    """Client requests current timer state."""
    sid = request.sid
    room_code = sid_to_room.get(sid)

    if not room_code or room_code not in mp_rooms:
        return

    room = mp_rooms[room_code]

    emit('timer_sync', {
        'white_time': room["white_time"],
        'black_time': room["black_time"],
        'active_timer': room["active_timer"],
        'game_started': room["game_started"],
        'game_over': room["game_over"]
    })


# ========== TIMER THREAD ==========
# Background thread to decrement timers
def timer_thread():
    import time
    while True:
        socketio.sleep(0.1)  # Update every 100ms

        for room_code, room in list(mp_rooms.items()):
            if not room["game_started"] or room["game_over"] or not room["timer_started"]:
                continue

            active = room["active_timer"]
            if not active:
                continue

            # Decrement by 0.1 seconds
            if active == 'white':
                room["white_time"] -= 0.1
                if room["white_time"] <= 0:
                    room["white_time"] = 0
                    room["game_over"] = True
                    room["result"] = "0-1"
                    room["active_timer"] = None
                    socketio.emit('game_over', {
                        'result': '0-1',
                        'reason': 'White ran out of time',
                        'message': 'White ran out of time! Black wins!'
                    }, room=room_code)
            else:
                room["black_time"] -= 0.1
                if room["black_time"] <= 0:
                    room["black_time"] = 0
                    room["game_over"] = True
                    room["result"] = "1-0"
                    room["active_timer"] = None
                    socketio.emit('game_over', {
                        'result': '1-0',
                        'reason': 'Black ran out of time',
                        'message': 'Black ran out of time! White wins!'
                    }, room=room_code)

            # Periodic timer broadcast (every ~1 second)
            if int(time.time() * 10) % 10 == 0:
                socketio.emit('timer_update', {
                    'white_time': room["white_time"],
                    'black_time': room["black_time"],
                    'active_timer': room["active_timer"]
                }, room=room_code)


# Start timer thread
@socketio.on('connect')
def start_timer_on_connect():
    # Timer thread is already running globally
    pass

# Start background thread
import threading
import time as time_module
timer_thread_obj = threading.Thread(target=timer_thread, daemon=True)
timer_thread_obj.start()


if __name__ == "__main__":
    socketio.run(app, debug=False)
