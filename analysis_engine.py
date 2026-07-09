"""
Stockfish-backed game review.

This module is completely separate from MattFish's own playing engine
(engine.py). MattFish keeps playing games against people with its own logic;
Stockfish is only ever invoked here, on demand, to score positions for the
post-game review page (accuracy %, move classifications, best-move hints).
"""

import os
import math
import threading
import chess
import chess.engine
import chess.pgn
import io

# Path to the Stockfish binary. On Render this is downloaded into ./bin at
# build time by build.sh. Override with the STOCKFISH_PATH env var if you
# place the binary somewhere else.
STOCKFISH_PATH = os.environ.get(
    "STOCKFISH_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "stockfish", "stockfish-ubuntu-x86-64"),
)

# Search depth used for each position during a review. Higher = more
# accurate classifications but slower (roughly linear-ish in time per ply).
# 14 is a good balance; drop to 10-12 if reviews feel too slow on your plan.
REVIEW_DEPTH = int(os.environ.get("REVIEW_DEPTH", "14"))

MATE_SCORE = 100000

_engine_lock = threading.Lock()
_engine = None


def _get_engine():
    """Lazily start (or restart) the Stockfish process. Guarded by a lock
    since gunicorn's default sync worker handles one request at a time per
    worker anyway, but this keeps it safe if that ever changes."""
    global _engine
    if _engine is not None:
        try:
            # cheap liveness check
            _engine.ping()
            return _engine
        except Exception:
            _engine = None

    if not os.path.exists(STOCKFISH_PATH):
        raise RuntimeError(
            f"Stockfish binary not found at {STOCKFISH_PATH}. "
            "Did build.sh run during deploy? See README for setup."
        )

    _engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    return _engine


def _cp_from_info(info, board):
    """Extract a White-perspective centipawn value from an analyse() result.
    Mate scores are converted to a large flat value (still correctly signed)
    so downstream math (win% conversion) treats them as decisive."""
    score = info["score"].white()
    return score.score(mate_score=MATE_SCORE)


def _mate_from_info(info):
    score = info["score"].white()
    m = score.mate()
    return m  # None if not a forced mate


def cp_to_win_percent(cp):
    """Lichess's published centipawn -> win% sigmoid."""
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def move_accuracy(win_before_mover, win_after_mover):
    """Lichess's published win%-drop -> per-move accuracy formula."""
    win_drop = max(0.0, win_before_mover - win_after_mover)
    acc = 103.1668 * math.exp(-0.04354 * win_drop) - 3.1669
    return max(0.0, min(100.0, acc))


def classify(loss_cp, ply, is_best_move):
    if is_best_move:
        return "Best"
    if ply < 10 and loss_cp <= 20:
        return "Book"
    if loss_cp >= 200:
        return "Blunder"
    if loss_cp >= 100:
        return "Mistake"
    if loss_cp >= 50:
        return "Inaccuracy"
    if loss_cp >= 20:
        return "Good"
    return "Excellent"


def analyze_pgn(pgn_text, depth=None):
    """Replay a PGN move by move, scoring every position once with Stockfish.
    Returns a dict with per-ply move data plus overall accuracy for both sides."""
    depth = depth or REVIEW_DEPTH

    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("Could not parse PGN. Check the move text and try again.")

    engine = _get_engine()
    limit = chess.engine.Limit(depth=depth)

    board = game.board()
    moves = list(game.mainline_moves())
    if not moves:
        raise ValueError("This PGN has no moves to analyze.")

    # Evaluate every position once: position 0 is the start, position i is
    # the board after move i has been played. n plies -> n+1 evaluations.
    positions_eval = []   # white-pov centipawns (mate collapsed to +-100000)
    positions_mate = []   # None or signed mate-in-N (white pov)
    positions_best = []   # suggested move (chess.Move) from that position, or None if game over there

    def eval_current():
        if board.is_game_over():
            if board.is_checkmate():
                # side to move is checkmated
                cp = -MATE_SCORE if board.turn == chess.WHITE else MATE_SCORE
                return cp, (0 if board.turn == chess.WHITE else 0), None
            return 0, None, None  # stalemate / draw
        info = engine.analyse(board, limit)
        cp = _cp_from_info(info, board)
        mate = _mate_from_info(info)
        best = info.get("pv", [None])[0]
        return cp, mate, best

    cp, mate, best = eval_current()
    positions_eval.append(cp)
    positions_mate.append(mate)
    positions_best.append(best)

    for move in moves:
        board.push(move)
        cp, mate, best = eval_current()
        positions_eval.append(cp)
        positions_mate.append(mate)
        positions_best.append(best)

    # Build per-ply move records
    replay = game.board()
    ply_data = []
    white_acc_list = []
    black_acc_list = []

    for i, move in enumerate(moves):
        mover_is_white = replay.turn == chess.WHITE
        san = replay.san(move)

        eval_before = positions_eval[i]
        eval_after = positions_eval[i + 1]
        best_move = positions_best[i]

        if mover_is_white:
            loss = max(0, eval_before - eval_after)
        else:
            loss = max(0, eval_after - eval_before)

        is_best = (best_move is not None and best_move == move)
        ply_classification = classify(loss, i, is_best)

        win_before_white = cp_to_win_percent(eval_before)
        win_after_white = cp_to_win_percent(eval_after)
        if mover_is_white:
            acc = move_accuracy(win_before_white, win_after_white)
            white_acc_list.append(acc)
        else:
            acc = move_accuracy(100 - win_before_white, 100 - win_after_white)
            black_acc_list.append(acc)

        replay.push(move)

        ply_data.append({
            "ply": i,
            "move_number": i // 2 + 1,
            "mover": "white" if mover_is_white else "black",
            "move_uci": move.uci(),
            "move_san": san,
            "fen": replay.fen(),
            "eval_cp": None if abs(eval_after) >= MATE_SCORE else eval_after,
            "mate": positions_mate[i + 1],
            "best_move_uci": best_move.uci() if best_move else None,
            "classification": ply_classification,
            "centipawn_loss": loss,
        })

    def avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    return {
        "moves": ply_data,
        "starting_fen": chess.STARTING_FEN,
        "white_accuracy": avg(white_acc_list),
        "black_accuracy": avg(black_acc_list),
        "white_name": game.headers.get("White", "White"),
        "black_name": game.headers.get("Black", "Black"),
        "result": game.headers.get("Result", "*"),
        "depth": depth,
    }


def shutdown_engine():
    global _engine
    if _engine is not None:
        try:
            _engine.quit()
        except Exception:
            pass
        _engine = None
