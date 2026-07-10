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

# Hard wall-clock ceiling for an entire review, spent across every position.
# Divided evenly across positions inside analyze_pgn() so a request can never
# run away and time out the whole HTTP request - deep/slow searches on a
# handful of ugly positions eat into the budget, and later positions in that
# same game automatically get less time each to compensate, rather than the
# whole review failing. This is what makes the "Precise" (depth 18) setting
# reliably finish instead of occasionally blowing past gunicorn's --timeout
# on long games.
REVIEW_TIME_BUDGET_SECONDS = float(os.environ.get("REVIEW_TIME_BUDGET_SECONDS", "150"))

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
    try:
        # More threads + hash = Stockfish searches faster and more accurately
        # at a given depth. Falls back silently on a single-core host (still
        # valid, just slower) - this is what makes "Precise" (depth 18)
        # actually finish in reasonable time instead of crawling on defaults
        # of Threads=1 / Hash=16MB.
        cpu_count = os.cpu_count() or 1
        threads = max(1, min(4, cpu_count))
        _engine.configure({"Threads": threads, "Hash": 128})
    except Exception:
        pass
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


def mover_pov_mate(mate_white_pov, mover_is_white):
    """Convert a white-perspective forced-mate count to the mover's own
    perspective. Positive = the mover has the forced mate; negative = the
    mover is getting forced-mated; None = no forced mate on the board."""
    if mate_white_pov is None:
        return None
    return mate_white_pov if mover_is_white else -mate_white_pov


def classify(win_drop, loss_cp, ply, is_best_move, mate_before_mover=None, mate_after_mover=None):
    """Classify a move using the drop in the mover's win probability (the
    same win%-drop metric Lichess's own classifier uses), not raw centipawn
    loss. Raw-cp thresholds mis-tag moves in already-decided positions: going
    from +900cp to +700cp is a 200cp "loss" but barely moves the needle on
    who's winning, so it isn't really a blunder - the old thresholds would
    have flagged it as one anyway. Win% drop scales correctly regardless of
    how lopsided the position already is."""
    if is_best_move:
        return "Best"
    if ply < 10 and loss_cp <= 20:
        return "Book"

    # Win% saturates near 0/100 once a mate is on the board, which can hide
    # a real error (e.g. letting a forced mate slip away, or mating two moves
    # slower than necessary). Catch that case explicitly before falling back
    # to the win%-drop thresholds.
    if mate_before_mover is not None and mate_before_mover > 0:
        if mate_after_mover is None or mate_after_mover <= 0:
            return "Blunder"  # had a forced mate, now it's gone entirely
        if mate_after_mover > mate_before_mover:
            return "Mistake"  # still mating, but slower than the best line

    if win_drop >= 20:
        return "Blunder"
    if win_drop >= 10:
        return "Mistake"
    if win_drop >= 5:
        return "Inaccuracy"
    if win_drop >= 2:
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

    board = game.board()
    moves = list(game.mainline_moves())
    if not moves:
        raise ValueError("This PGN has no moves to analyze.")

    # Spend the wall-clock budget evenly across every position that needs
    # scoring. Short games get generous time per position (searches usually
    # still finish well before the cap); long games automatically get a
    # smaller per-position slice so the whole review still lands inside the
    # budget instead of timing out.
    num_positions = len(moves) + 1
    per_position_time = max(0.3, REVIEW_TIME_BUDGET_SECONDS / num_positions)
    limit = chess.engine.Limit(depth=depth, time=per_position_time)

    # Evaluate every position once: position 0 is the start, position i is
    # the board after move i has been played. n plies -> n+1 evaluations.
    positions_eval = []   # white-pov centipawns (mate collapsed to +-100000)
    positions_mate = []   # None or signed mate-in-N (white pov)
    positions_best = []   # suggested move (chess.Move) from that position, or None if game over there

    def eval_current():
        if board.is_game_over():
            if board.is_checkmate():
                # side to move (board.turn) is the one who just got mated.
                # Sign convention matches cp: negative white-pov = bad for
                # white. Magnitude is irrelevant here since the game is over
                # - only the sign matters downstream for classify()'s
                # mate-aware override.
                cp = -MATE_SCORE if board.turn == chess.WHITE else MATE_SCORE
                mate = -1 if board.turn == chess.WHITE else 1
                return cp, mate, None
            return 0, None, None  # stalemate / draw
        info = engine.analyse(board, limit)
        cp = _cp_from_info(info, board)
        mate = _mate_from_info(info)
        best = info.get("pv", [None])[0]
        return cp, mate, best

    # A single Stockfish process is reused across requests. The lock keeps
    # that safe if this ever runs with more than one thread touching the
    # engine at once (e.g. a threaded dev server) - gunicorn's default sync
    # worker already serializes requests, so this is a no-op cost there.
    with _engine_lock:
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

        win_before_white = cp_to_win_percent(eval_before)
        win_after_white = cp_to_win_percent(eval_after)
        win_before_mover = win_before_white if mover_is_white else (100 - win_before_white)
        win_after_mover = win_after_white if mover_is_white else (100 - win_after_white)
        win_drop = max(0.0, win_before_mover - win_after_mover)

        acc = move_accuracy(win_before_mover, win_after_mover)
        if mover_is_white:
            white_acc_list.append(acc)
        else:
            black_acc_list.append(acc)

        mate_before_mover = mover_pov_mate(positions_mate[i], mover_is_white)
        mate_after_mover = mover_pov_mate(positions_mate[i + 1], mover_is_white)
        ply_classification = classify(win_drop, loss, i, is_best, mate_before_mover, mate_after_mover)

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
