import eventlet
eventlet.monkey_patch()
import os
from flask import Flask, render_template, jsonify, request, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import secrets
import chess
from engine import search as local_search
import requests
import chess.pgn
import io
from collections import defaultdict
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=True, engineio_logger=True)


# ========== HEALTH CHECK ==========
@app.route("/health")
def health():
    return jsonify({"status": "ok"})
    
# ========== MULTIPLAYER GAME STATE ==========
rooms = {}

# ========== LICHESS CLOUD API ==========
LICHESS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (MattFish Chess App)"
}

def get_lichess_cloud_eval(fen):
    try:
        url = "https://lichess.org/api/cloud-eval"
        params = {"fen": fen, "multiPv": 1}
        response = requests.get(url, params=params, headers=LICHESS_HEADERS, timeout=3)

        if response.status_code == 429:
            return None
        if response.status_code != 200:
            return None

        data = response.json()
        if "pvs" not in data or not data["pvs"]:
            return None

        pv = data["pvs"][0]
        best_move = pv.get("moves", "").split()[0] if "moves" in pv else None

        if "mate" in pv:
            return (None, pv["mate"], best_move)
        elif "cp" in pv:
            return (pv["cp"], 0, best_move)

        return None
    except Exception as e:
        return None

# ========== CHESS GAME (vs Engine) ==========
games = {}

@app.route("/play")
def play():
    return render_template("chess.html")

@app.route("/play-friend")
def play_friend():
    return render_template("play_friend.html")

@app.route("/spectate")
def spectate():
    return render_template("spectate.html")

@app.route("/overlay")
def overlay():
    return render_template("overlay.html")

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

    lichess_result = get_lichess_cloud_eval(board.fen())

    if lichess_result is not None:
        eval_cp, mate, _ = lichess_result
        if mate != 0:
            return jsonify({"eval": None, "mate": mate})
        else:
            return jsonify({"eval": eval_cp, "mate": 0})

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
    lichess_result = get_lichess_cloud_eval(board.fen())

    if lichess_result is not None:
        _, _, best_move_uci = lichess_result
        if best_move_uci:
            try:
                move = chess.Move.from_uci(best_move_uci)
                if move in board.legal_moves:
                    return move
            except:
                pass

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

# ========== MULTIPLAYER SOCKET.IO EVENTS ==========

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    print(f'Client disconnected: {sid}')
    for room_code, room_data in list(rooms.items()):
        if sid in room_data.get('players', {}):
            color = room_data['players'][sid]
            del room_data['players'][sid]
            emit('player_left', {'color': color, 'message': f'{color.capitalize()} player left the game'}, room=room_code)
            if not room_data['players']:
                del rooms[room_code]
            break
        if sid in room_data.get('spectators', []):
            room_data['spectators'].remove(sid)

@socketio.on('create_room')
def handle_create_room(data):
    sid = request.sid
    room_code = secrets.token_hex(3).upper()

    color = data.get('color', 'white')
    opponent_color = 'black' if color == 'white' else 'white'

    rooms[room_code] = {
        'players': {sid: color},
        'board': chess.Board(),
        'spectators': [],
        'chat': [],
        'status': 'waiting',
        'time_control': data.get('time_control', {'minutes': 10, 'increment': 0}),
        'timers': {color: data.get('time_control', {'minutes': 10, 'increment': 0})['minutes'] * 60,
                   opponent_color: data.get('time_control', {'minutes': 10, 'increment': 0})['minutes'] * 60},
        'last_move_time': None,
        'game_result': None
    }

    join_room(room_code)
    emit('room_created', {'room_code': room_code, 'your_color': color})

@socketio.on('join_room')
def handle_join_room(data):
    sid = request.sid
    room_code = data.get('room_code', '').upper().strip()

    if room_code not in rooms:
        emit('error', {'message': 'Room not found'})
        return

    room = rooms[room_code]

    if len(room['players']) >= 2:
        # Join as spectator
        room['spectators'].append(sid)
        join_room(room_code)
        emit('joined_as_spectator', {
            'room_code': room_code,
            'fen': room['board'].fen(),
            'chat': room['chat'],
            'status': room['status']
        })
        emit('spectator_joined', {'count': len(room['spectators'])}, room=room_code, include_self=False)
        return

    # Join as player
    taken_colors = set(room['players'].values())
    your_color = 'black' if 'white' in taken_colors else 'white'
    room['players'][sid] = your_color
    join_room(room_code)

    # Tell the joiner they got in
    emit('joined_room', {
        'room_code': room_code,
        'your_color': your_color,
        'fen': room['board'].fen()
    })

    # Start the game and tell EVERYONE in the room
    room['status'] = 'playing'
    room['last_move_time'] = time.time()
    
    # THIS IS THE FIX: socketio.emit broadcasts to all in room
    socketio.emit('game_started', {
        'room_code': room_code,
        'fen': room['board'].fen(),
        'white_player': [s for s, c in room['players'].items() if c == 'white'][0],
        'black_player': [s for s, c in room['players'].items() if c == 'black'][0],
        'time_control': room['time_control']
    }, room=room_code)
    # Start the game!
    room['status'] = 'playing'
    room['last_move_time'] = time.time()
    
    # Emit game_started to BOTH players (including the creator)
    emit('game_started', {
        'room_code': room_code,
        'fen': room['board'].fen(),
        'white_player': [s for s, c in room['players'].items() if c == 'white'][0],
        'black_player': [s for s, c in room['players'].items() if c == 'black'][0],
        'time_control': room['time_control']
    }, room=room_code)

@socketio.on('make_move')
def handle_make_move(data):
    sid = request.sid
    room_code = data.get('room_code', '').upper().strip()
    move_uci = data.get('move')

    if room_code not in rooms:
        emit('error', {'message': 'Room not found'})
        return

    room = rooms[room_code]

    if sid not in room['players']:
        emit('error', {'message': 'Not a player in this room'})
        return

    if room['status'] != 'playing':
        emit('error', {'message': 'Game not in progress'})
        return

    player_color = room['players'][sid]
    board = room['board']

    expected_turn = 'white' if board.turn == chess.WHITE else 'black'
    if player_color != expected_turn:
        emit('error', {'message': 'Not your turn'})
        return

    try:
        move = chess.Move.from_uci(move_uci)
        if move not in board.legal_moves:
            emit('error', {'message': 'Illegal move'})
            return

        board.push(move)

        now = time.time()
        elapsed = now - room['last_move_time']
        room['timers'][player_color] -= elapsed
        room['timers'][player_color] += room['time_control']['increment']
        room['last_move_time'] = now

        if room['timers'][player_color] <= 0:
            room['timers'][player_color] = 0
            room['status'] = 'finished'
            room['game_result'] = '0-1' if player_color == 'white' else '1-0'
            emit('game_over', {
                'result': room['game_result'],
                'reason': 'timeout',
                'loser': player_color
            }, room=room_code)
            return

        game_over = board.is_game_over()
        result = None

        if game_over:
            room['status'] = 'finished'
            room['game_result'] = board.result()
            emit('game_over', {
                'result': room['game_result'],
                'reason': 'checkmate' if board.is_checkmate() else 'draw'
            }, room=room_code)

        emit('move_made', {
            'move': move_uci,
            'fen': board.fen(),
            'player_color': player_color,
            'legal_moves': [str(m) for m in board.legal_moves] if not game_over else [],
            'check': board.is_check(),
            'timers': room['timers'],
            'game_over': game_over,
            'result': result
        }, room=room_code)

    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('send_chat')
def handle_chat(data):
    sid = request.sid
    room_code = data.get('room_code', '').upper().strip()
    message = data.get('message', '').strip()

    if room_code not in rooms or not message:
        return

    room = rooms[room_code]

    if sid in room['players']:
        sender = room['players'][sid]
        sender_name = sender.capitalize()
    else:
        sender = 'spectator'
        sender_name = f'Spectator {room["spectators"].index(sid) + 1}'

    chat_msg = {
        'sender': sender_name,
        'message': message,
        'timestamp': time.time()
    }
    room['chat'].append(chat_msg)

    if len(room['chat']) > 100:
        room['chat'] = room['chat'][-100:]

    emit('chat_message', chat_msg, room=room_code)

@socketio.on('send_preset_message')
def handle_preset_message(data):
    sid = request.sid
    room_code = data.get('room_code', '').upper().strip()
    preset = data.get('preset')

    presets = {
        'gl': 'Good luck!',
        'hf': 'Have fun!',
        'gg': 'Good game!',
        'wp': 'Well played!',
        'ty': 'Thank you!',
        'oops': 'Oops!',
        'nice': 'Nice move!',
        'think': 'Let me think...',
        'brb': 'Be right back',
        'hello': 'Hello!'
    }

    message = presets.get(preset, preset)
    handle_chat({'room_code': room_code, 'message': message})

@socketio.on('offer_draw')
def handle_offer_draw(data):
    sid = request.sid
    room_code = data.get('room_code', '').upper().strip()

    if room_code not in rooms:
        return

    room = rooms[room_code]
    if sid not in room['players']:
        return

    player_color = room['players'][sid]
    emit('draw_offered', {'by': player_color}, room=room_code, include_self=False)

@socketio.on('respond_draw')
def handle_respond_draw(data):
    sid = request.sid
    room_code = data.get('room_code', '').upper().strip()
    accepted = data.get('accepted', False)

    if room_code not in rooms:
        return

    room = rooms[room_code]
    if accepted:
        room['status'] = 'finished'
        room['game_result'] = '1/2-1/2'
        emit('game_over', {
            'result': '1/2-1/2',
            'reason': 'draw agreed'
        }, room=room_code)
    else:
        emit('draw_declined', {}, room=room_code)

@socketio.on('resign')
def handle_resign(data):
    sid = request.sid
    room_code = data.get('room_code', '').upper().strip()

    if room_code not in rooms:
        return

    room = rooms[room_code]
    if sid not in room['players']:
        return

    player_color = room['players'][sid]
    room['status'] = 'finished'
    room['game_result'] = '0-1' if player_color == 'white' else '1-0'
    emit('game_over', {
        'result': room['game_result'],
        'reason': 'resignation',
        'resigner': player_color
    }, room=room_code)

@socketio.on('request_sync')
def handle_request_sync(data):
    sid = request.sid
    room_code = data.get('room_code', '').upper().strip()

    if room_code not in rooms:
        return

    room = rooms[room_code]
    emit('sync_state', {
        'fen': room['board'].fen(),
        'status': room['status'],
        'timers': room['timers'],
        'chat': room['chat'],
        'result': room.get('game_result'),
        'legal_moves': [str(m) for m in room['board'].legal_moves] if room['status'] == 'playing' else []
    })

# ========== CHESS.COM STATS ==========
headers = {"User-Agent": "Mozilla/5.0"}

@app.route("/")
def index():
    return render_template("index.html")

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
    socketio.run(app, debug=False)
