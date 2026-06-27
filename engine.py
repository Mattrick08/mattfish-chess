import chess
import time
import random

# Piece-square tables
PAWN_TABLE = [
     0,   0,   0,   0,   0,   0,   0,   0,
    50,  50,  50,  50,  50,  50,  50,  50,
    10,  10,  20,  30,  30,  20,  10,  10,
     5,   5,  10,  25,  25,  10,   5,   5,
     0,   0,   0,  20,  20,   0,   0,   0,
     5,  -5, -10,   0,   0, -10,  -5,   5,
     5,  10,  10, -20, -20,  10,  10,   5,
     0,   0,   0,   0,   0,   0,   0,   0
]

KNIGHT_TABLE = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20,   0,   0,   0,   0, -20, -40,
    -30,   0,  10,  15,  15,  10,   0, -30,
    -30,   5,  15,  20,  20,  15,   5, -30,
    -30,   0,  15,  20,  20,  15,   0, -30,
    -30,   5,  10,  15,  15,  10,   5, -30,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50
]

BISHOP_TABLE = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -10,   0,   5,  10,  10,   5,   0, -10,
    -10,   5,   5,  10,  10,   5,   5, -10,
    -10,   0,  10,  10,  10,  10,   0, -10,
    -10,  10,  10,  10,  10,  10,  10, -10,
    -10,   5,   0,   0,   0,   0,   5, -10,
    -20, -10, -10, -10, -10, -10, -10, -20
]

ROOK_TABLE = [
     0,   0,   0,   0,   0,   0,   0,   0,
     5,  10,  10,  10,  10,  10,  10,   5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
     0,   0,   0,   5,   5,   0,   0,   0
]

QUEEN_TABLE = [
    -20, -10, -10,  -5,  -5, -10, -10, -20,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -10,   0,   5,   5,   5,   5,   0, -10,
     -5,   0,   5,   5,   5,   5,   0,  -5,
      0,   0,   5,   5,   5,   5,   0,  -5,
    -10,   5,   5,   5,   5,   5,   0, -10,
    -10,   0,   5,   0,   0,   0,   0, -10,
    -20, -10, -10,  -5,  -5, -10, -10, -20
]

KING_MG_TABLE = [
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
     20,  20,   0,   0,   0,   0,  20,  20,
     20,  30,  10,   0,   0,  10,  30,  20
]

KING_EG_TABLE = [
    -50, -40, -30, -20, -20, -30, -40, -50,
    -30, -20, -10,   0,   0, -10, -20, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -30,   0,   0,   0,   0, -30, -30,
    -50, -30, -30, -30, -30, -30, -30, -50
]

PIECE_TABLES = {
    chess.PAWN: PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE,
    chess.KING: KING_MG_TABLE
}

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# Search globals
killer_moves = {}
history_table = {}
NODES_SEARCHED = 0
START_TIME = 0
TIME_LIMIT = 0

def should_stop():
    if TIME_LIMIT > 0 and time.time() - START_TIME > TIME_LIMIT:
        return True
    return False

def clear_search_data():
    killer_moves.clear()
    history_table.clear()

# ========== EVALUATION ==========

def get_position_bonus(piece_type, square, color):
    table = PIECE_TABLES[piece_type]
    if color == chess.WHITE:
        index = (7 - chess.square_rank(square)) * 8 + chess.square_file(square)
    else:
        index = chess.square_rank(square) * 8 + chess.square_file(square)
    return table[index]

def count_material(board):
    total = 0
    for piece_type in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        total += len(board.pieces(piece_type, chess.WHITE)) * PIECE_VALUES[piece_type]
        total += len(board.pieces(piece_type, chess.BLACK)) * PIECE_VALUES[piece_type]
    return total

def is_endgame(board):
    white_queens = len(board.pieces(chess.QUEEN, chess.WHITE))
    black_queens = len(board.pieces(chess.QUEEN, chess.BLACK))
    if white_queens == 0 and black_queens == 0:
        return True
    material = count_material(board)
    return material < 2600

def evaluate_pawn_structure(board, color):
    score = 0
    pawns = board.pieces(chess.PAWN, color)
    enemy_pawns = board.pieces(chess.PAWN, not color)
    files_with_pawns = set()
    for sq in pawns:
        files_with_pawns.add(chess.square_file(sq))
    for sq in pawns:
        file_idx = chess.square_file(sq)
        rank_idx = chess.square_rank(sq)
        same_file = sum(1 for p in pawns if chess.square_file(p) == file_idx)
        if same_file > 1:
            score -= 20 * (same_file - 1)
        adjacent_files = [file_idx - 1, file_idx + 1]
        has_neighbor = any(f in files_with_pawns for f in adjacent_files if 0 <= f <= 7)
        if not has_neighbor:
            score -= 15
        if color == chess.WHITE:
            enemy_ranks = [chess.square_rank(p) for p in enemy_pawns if chess.square_file(p) == file_idx]
            if not enemy_ranks or all(r < rank_idx for r in enemy_ranks):
                score += 20 + 10 * rank_idx
        else:
            enemy_ranks = [chess.square_rank(p) for p in enemy_pawns if chess.square_file(p) == file_idx]
            if not enemy_ranks or all(r > rank_idx for r in enemy_ranks):
                score += 20 + 10 * (7 - rank_idx)
    return score if color == chess.WHITE else -score

def evaluate_piece_safety(board, color):
    score = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.color == color:
            attackers = len(list(board.attackers(not color, square)))
            defenders = len(list(board.attackers(color, square)))
            if attackers > 0:
                piece_val = PIECE_VALUES.get(piece.piece_type, 0)
                if attackers > defenders:
                    score -= piece_val // 2
                elif attackers == defenders:
                    score -= piece_val // 8
    return score

def evaluate_mobility(board):
    if board.is_game_over():
        return 0
    white_mobility = 0
    black_mobility = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            attacks = len(list(board.attacks(square)))
            if piece.color == chess.WHITE:
                white_mobility += attacks
            else:
                black_mobility += attacks
    return (white_mobility - black_mobility) * 2

def evaluate_king_safety(board):
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        king_sq = board.king(color)
        if king_sq is None:
            continue
        king_file = chess.square_file(king_sq)
        king_rank = chess.square_rank(king_sq)
        pawn_shield = 0
        direction = 1 if color == chess.WHITE else -1
        for df in [-1, 0, 1]:
            for dr in [1, 2]:
                check_file = king_file + df
                check_rank = king_rank + dr * direction
                if 0 <= check_file <= 7 and 0 <= check_rank <= 7:
                    sq = chess.square(check_file, check_rank)
                    piece = board.piece_at(sq)
                    if piece and piece.piece_type == chess.PAWN and piece.color == color:
                        pawn_shield += 10
        open_file_penalty = 0
        for df in [-1, 0, 1]:
            check_file = king_file + df
            if 0 <= check_file <= 7:
                has_pawn = False
                for rank in range(8):
                    sq = chess.square(check_file, rank)
                    piece = board.piece_at(sq)
                    if piece and piece.piece_type == chess.PAWN:
                        has_pawn = True
                        break
                if not has_pawn:
                    open_file_penalty += 15
        king_safety = pawn_shield - open_file_penalty
        if color == chess.WHITE:
            score += king_safety
        else:
            score -= king_safety
    return score

def evaluate_piece_activity(board):
    score = 0
    white_bishops = len(board.pieces(chess.BISHOP, chess.WHITE))
    black_bishops = len(board.pieces(chess.BISHOP, chess.BLACK))
    if white_bishops >= 2:
        score += 30
    if black_bishops >= 2:
        score -= 30
    for color in [chess.WHITE, chess.BLACK]:
        rooks = board.pieces(chess.ROOK, color)
        for sq in rooks:
            file_idx = chess.square_file(sq)
            pawns_on_file = sum(1 for p in board.pieces(chess.PAWN, color) if chess.square_file(p) == file_idx)
            enemy_pawns_on_file = sum(1 for p in board.pieces(chess.PAWN, not color) if chess.square_file(p) == file_idx)
            if pawns_on_file == 0 and enemy_pawns_on_file == 0:
                if color == chess.WHITE:
                    score += 20
                else:
                    score -= 20
            elif pawns_on_file == 0:
                if color == chess.WHITE:
                    score += 10
                else:
                    score -= 10
    for color in [chess.WHITE, chess.BLACK]:
        knights = board.pieces(chess.KNIGHT, color)
        for sq in knights:
            rank = chess.square_rank(sq)
            if (color == chess.WHITE and rank >= 4) or (color == chess.BLACK and rank <= 3):
                protected = False
                for attacker in board.attackers(color, sq):
                    p = board.piece_at(attacker)
                    if p and p.piece_type == chess.PAWN:
                        protected = True
                        break
                if protected:
                    enemy_pawn_attack = False
                    for attacker in board.attackers(not color, sq):
                        p = board.piece_at(attacker)
                        if p and p.piece_type == chess.PAWN:
                            enemy_pawn_attack = True
                            break
                    if not enemy_pawn_attack:
                        if color == chess.WHITE:
                            score += 25
                        else:
                            score -= 25
    return score

def evaluate(board):
    """Evaluate from White's perspective. Positive = White is better."""
    if board.is_checkmate():
        return -99999
    if board.is_stalemate() or board.is_insufficient_material() or board.halfmove_clock >= 100 or board.is_repetition(3):
        return 0
    score = 0
    endgame = is_endgame(board)
    for piece_type in PIECE_VALUES:
        for square in board.pieces(piece_type, chess.WHITE):
            score += PIECE_VALUES[piece_type]
            if piece_type == chess.KING and endgame:
                score += KING_EG_TABLE[(7 - chess.square_rank(square)) * 8 + chess.square_file(square)]
            else:
                score += get_position_bonus(piece_type, square, chess.WHITE)
        for square in board.pieces(piece_type, chess.BLACK):
            score -= PIECE_VALUES[piece_type]
            if piece_type == chess.KING and endgame:
                score -= KING_EG_TABLE[chess.square_rank(square) * 8 + chess.square_file(square)]
            else:
                score -= get_position_bonus(piece_type, square, chess.BLACK)
    score += evaluate_pawn_structure(board, chess.WHITE)
    score -= evaluate_pawn_structure(board, chess.BLACK)
    score += evaluate_piece_safety(board, chess.WHITE)
    score -= evaluate_piece_safety(board, chess.BLACK)
    score += evaluate_piece_activity(board)
    score += evaluate_mobility(board)
    if not endgame:
        score += evaluate_king_safety(board)
    return score

# ========== MOVE ORDERING ==========

def get_move_score(board, move, depth, ply):
    score = 0
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        if victim:
            victim_val = PIECE_VALUES.get(victim.piece_type, 0)
            attacker_val = PIECE_VALUES.get(attacker.piece_type, 0) if attacker else 0
            score += 1000000 + victim_val * 10 - attacker_val
        else:
            score += 500000
    if move.promotion:
        promo_value = PIECE_VALUES.get(move.promotion, 0)
        score += 800000 + promo_value
    if ply in killer_moves:
        if move in killer_moves[ply]:
            score += 90000
    hist_key = (move.from_square, move.to_square)
    if hist_key in history_table:
        score += min(history_table[hist_key], 80000)
    board.push(move)
    if board.is_check():
        score += 40000
    board.pop()
    return score

def order_moves(board, depth, ply, hash_move=None):
    moves = list(board.legal_moves)
    scored = []
    for move in moves:
        if hash_move and move == hash_move:
            scored.append((move, 10000000))
        else:
            scored.append((move, get_move_score(board, move, depth, ply)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [m for m, s in scored]

# ========== QUIESCENCE SEARCH ==========

Q_DELTA = 900

def quiescence_search(board, alpha, beta, depth=0):
    stand_pat = evaluate(board)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat
    if stand_pat + Q_DELTA < alpha:
        return alpha
    captures = [m for m in board.legal_moves if board.is_capture(m)]
    if depth < 2:
        checks = []
        for m in board.legal_moves:
            if m not in captures:
                board.push(m)
                if board.is_check():
                    checks.append(m)
                board.pop()
        captures.extend(checks)
    def capture_score(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        if victim:
            v = PIECE_VALUES.get(victim.piece_type, 0)
            a = PIECE_VALUES.get(attacker.piece_type, 0) if attacker else 0
            return v * 10 - a
        return 0
    captures.sort(key=capture_score, reverse=True)
    for move in captures:
        board.push(move)
        score = -quiescence_search(board, -beta, -alpha, depth + 1)
        board.pop()
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha

# ========== MAIN SEARCH ==========

def alpha_beta(board, depth, alpha, beta, ply):
    """Negamax alpha-beta search."""
    global NODES_SEARCHED
    NODES_SEARCHED += 1
    if should_stop():
        return 0, None
    if board.is_game_over():
        if board.is_checkmate():
            return -99999 + ply, None
        return 0, None
    if board.halfmove_clock >= 100 or board.is_repetition(3):
        return 0, None
    if depth <= 0:
        score = quiescence_search(board, alpha, beta)
        return score, None
    moves = order_moves(board, depth, ply)
    if not moves:
        return evaluate(board), None
    best_move = None
    for move in moves:
        if should_stop():
            return 0, None
        board.push(move)
        score, _ = alpha_beta(board, depth - 1, -beta, -alpha, ply + 1)
        score = -score
        board.pop()
        if score >= beta:
            if not board.is_capture(move):
                if ply not in killer_moves:
                    killer_moves[ply] = [move, None]
                else:
                    killer_moves[ply][1] = killer_moves[ply][0]
                    killer_moves[ply][0] = move
                hist_key = (move.from_square, move.to_square)
                history_table[hist_key] = history_table.get(hist_key, 0) + depth * depth
            return beta, move
        if score > alpha:
            alpha = score
            best_move = move
    return alpha, best_move

def iterative_deepening(board, max_depth, time_limit):
    global NODES_SEARCHED, START_TIME, TIME_LIMIT
    NODES_SEARCHED = 0
    START_TIME = time.time()
    TIME_LIMIT = time_limit
    clear_search_data()

    best_move = None
    best_score = 0
    for depth in range(1, max_depth + 1):
        if should_stop() and best_move is not None:
            break
        score, move = alpha_beta(board, depth, -99999, 99999, 0)
        if should_stop() and best_move is not None:
            break
        if move:
            best_score = score
            best_move = move
            if abs(best_score) > 90000:
                break
    if best_move is None:
        score, move = alpha_beta(board, 1, -99999, 99999, 0)
        if move:
            best_move = move
            best_score = score
    if best_move is None and board.legal_moves.count() > 0:
        best_move = list(board.legal_moves)[0]
        best_score = evaluate(board)
    return best_score, best_move

def search(board, max_depth, time_limit=0):
    """Main entry point. Returns (score, move)."""
    return iterative_deepening(board, max_depth, time_limit)
