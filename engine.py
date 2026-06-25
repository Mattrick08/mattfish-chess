import chess
import time
import random

# =============================================================================
# PIECE SQUARE TABLES (improved - more nuanced values)
# =============================================================================

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

# King tables: middle game vs endgame (simplified - just one for now)
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

# =============================================================================
# OPENING BOOK (common first few moves to avoid early blunders)
# =============================================================================

OPENING_BOOK = {
    # Starting position responses for White
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -": [
        "e2e4", "d2d4", "c2c4", "g1f3"
    ],
    # After 1.e4
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq -": [
        "e7e5", "c7c5", "e7e6", "c7c6"
    ],
    # After 1.e4 e5
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": [
        "g1f3", "f1c4", "b1c3"
    ],
    # After 1.e4 e5 2.Nf3
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq -": [
        "b8c6", "g8f6", "d7d6"
    ],
    # After 1.d4
    "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq -": [
        "d7d5", "g8f6", "e7e6"
    ],
    # After 1.d4 d5
    "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq -": [
        "c2c4", "g1f3", "b1c3"
    ],
    # After 1.d4 d5 2.c4
    "rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq -": [
        "d5c4", "e7e6", "c7c6"
    ],
    # After 1.e4 c5 (Sicilian)
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": [
        "g1f3", "b1c3", "f2f4"
    ],
    # After 1.e4 e6 (French)
    "rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": [
        "d2d4", "d2d3"
    ],
    # After 1.e4 c6 (Caro-Kann)
    "rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": [
        "d2d4", "b1c3", "d2d3"
    ],
    # After 1.c4 (English)
    "rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR b KQkq -": [
        "e7e5", "c7c5", "g8f6", "e7e6"
    ],
    # After 1.Nf3
    "rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq -": [
        "d7d5", "g8f6", "c7c5"
    ],
}

# =============================================================================
# TRANSPOSITION TABLE
# =============================================================================

class TranspositionTable:
    def __init__(self, max_size=100000):
        self.table = {}
        self.max_size = max_size
        self.hits = 0
        self.lookups = 0

    def get(self, key):
        self.lookups += 1
        if key in self.table:
            self.hits += 1
            return self.table[key]
        return None

    def store(self, key, depth, score, flag, best_move):
        # Replace if deeper search or same depth
        if key in self.table:
            old = self.table[key]
            if depth < old[0]:
                return

        self.table[key] = (depth, score, flag, best_move)

        # Simple eviction if too big
        if len(self.table) > self.max_size:
            # Remove 10% oldest (simple: just clear half)
            keys = list(self.table.keys())
            for k in keys[:len(keys)//2]:
                del self.table[k]

    def clear(self):
        self.table.clear()
        self.hits = 0
        self.lookups = 0

# Global transposition table
tt = TranspositionTable(max_size=200000)

# =============================================================================
# ZOBRIST HASHING (for transposition table keys)
# =============================================================================

# Pre-compute random Zobrist keys
random.seed(42)  # Deterministic for consistency
ZOBRIST_KEYS = {}

# Piece keys
for color in [chess.WHITE, chess.BLACK]:
    for piece_type in chess.PIECE_TYPES:
        for square in chess.SQUARES:
            ZOBRIST_KEYS[(color, piece_type, square)] = random.getrandbits(64)

# Side to move key
ZOBRIST_SIDE = random.getrandbits(64)

# Castling rights keys (using string identifiers)
ZOBRIST_CASTLING = {
    "white_kingside": random.getrandbits(64),
    "white_queenside": random.getrandbits(64),
    "black_kingside": random.getrandbits(64),
    "black_queenside": random.getrandbits(64),
}

# En passant file keys
ZOBRIST_EN_PASSANT = [random.getrandbits(64) for _ in range(8)]

def compute_hash(board):
    """Compute Zobrist hash for a board position."""
    h = 0

    # Pieces
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            h ^= ZOBRIST_KEYS[(piece.color, piece.piece_type, square)]

    # Side to move
    if board.turn == chess.BLACK:
        h ^= ZOBRIST_SIDE

    # Castling rights
    if board.has_castling_rights(chess.WHITE):
        if board.has_kingside_castling_rights(chess.WHITE):
            h ^= ZOBRIST_CASTLING["white_kingside"]
        if board.has_queenside_castling_rights(chess.WHITE):
            h ^= ZOBRIST_CASTLING["white_queenside"]
    if board.has_castling_rights(chess.BLACK):
        if board.has_kingside_castling_rights(chess.BLACK):
            h ^= ZOBRIST_CASTLING["black_kingside"]
        if board.has_queenside_castling_rights(chess.BLACK):
            h ^= ZOBRIST_CASTLING["black_queenside"]

    # En passant
    if board.ep_square:
        h ^= ZOBRIST_EN_PASSANT[chess.square_file(board.ep_square)]

    return h

# =============================================================================
# EVALUATION
# =============================================================================

def get_position_bonus(piece_type, square, color):
    table = PIECE_TABLES[piece_type]
    if color == chess.WHITE:
        index = (7 - chess.square_rank(square)) * 8 + chess.square_file(square)
    else:
        index = chess.square_rank(square) * 8 + chess.square_file(square)
    return table[index]

def count_material(board):
    """Count total material on board (for endgame detection)."""
    total = 0
    for piece_type in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        total += len(board.pieces(piece_type, chess.WHITE)) * PIECE_VALUES[piece_type]
        total += len(board.pieces(piece_type, chess.BLACK)) * PIECE_VALUES[piece_type]
    return total

def is_endgame(board):
    """Determine if we're in endgame (no queens or very little material)."""
    white_queens = len(board.pieces(chess.QUEEN, chess.WHITE))
    black_queens = len(board.pieces(chess.QUEEN, chess.BLACK))

    if white_queens == 0 and black_queens == 0:
        return True

    material = count_material(board)
    return material < 2600  # Less than ~R+N+B worth of material besides queens

def evaluate_pawn_structure(board, color):
    """Evaluate pawn structure: doubled, isolated, passed pawns."""
    score = 0
    pawns = board.pieces(chess.PAWN, color)
    enemy_pawns = board.pieces(chess.PAWN, not color)

    files_with_pawns = set()
    for sq in pawns:
        files_with_pawns.add(chess.square_file(sq))

    for sq in pawns:
        file_idx = chess.square_file(sq)
        rank_idx = chess.square_rank(sq)

        # Doubled pawns penalty
        same_file = sum(1 for p in pawns if chess.square_file(p) == file_idx)
        if same_file > 1:
            score -= 20 * (same_file - 1)

        # Isolated pawn penalty
        adjacent_files = [file_idx - 1, file_idx + 1]
        has_neighbor = any(f in files_with_pawns for f in adjacent_files if 0 <= f <= 7)
        if not has_neighbor:
            score -= 15

        # Passed pawn bonus
        if color == chess.WHITE:
            enemy_ranks = [chess.square_rank(p) for p in enemy_pawns if chess.square_file(p) == file_idx]
            if not enemy_ranks or all(r < rank_idx for r in enemy_ranks):
                score += 20 + 10 * rank_idx
        else:
            enemy_ranks = [chess.square_rank(p) for p in enemy_pawns if chess.square_file(p) == file_idx]
            if not enemy_ranks or all(r > rank_idx for r in enemy_ranks):
                score += 20 + 10 * (7 - rank_idx)

    return score if color == chess.WHITE else -score

def evaluate_mobility(board):
    """Count legal moves for both sides (simplified mobility)."""
    # This is expensive to compute, so we approximate
    # We'll skip this in favor of faster evaluation
    return 0

def evaluate_king_safety(board):
    """Evaluate king safety: pawn shield, open files near king."""
    score = 0

    for color in [chess.WHITE, chess.BLACK]:
        king_sq = board.king(color)
        if king_sq is None:
            continue

        king_file = chess.square_file(king_sq)
        king_rank = chess.square_rank(king_sq)

        # Pawn shield
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

        # Open files near king (penalty)
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

def evaluate(board):
    # Check for checkmate
    if board.is_checkmate():
        if board.turn == chess.WHITE:
            return -99999
        else:
            return 99999

    # Draw conditions
    if board.is_stalemate() or board.is_insufficient_material() or board.halfmove_clock >= 100 or board.is_repetition(3):
        return 0

    score = 0
    endgame = is_endgame(board)

    # Material + position
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

    # Pawn structure
    score += evaluate_pawn_structure(board, chess.WHITE)
    score -= evaluate_pawn_structure(board, chess.BLACK)

    # King safety (only in middle game)
    if not endgame:
        score += evaluate_king_safety(board)

    # Tempo bonus (side to move gets small bonus)
    if board.turn == chess.WHITE:
        score += 10
    else:
        score -= 10

    return score

# =============================================================================
# MOVE ORDERING
# =============================================================================

# Killer moves: store 2 killer moves per ply
killer_moves = {}

# History heuristic
history_table = {}

def clear_search_data():
    """Clear killer moves and history between searches."""
    killer_moves.clear()
    history_table.clear()

def get_move_score(board, move, depth, ply):
    """Score a move for ordering. Higher = better."""
    score = 0

    # Hash move (from transposition table) - highest priority
    # This is handled separately in the search

    # Captures (MVV-LVA)
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        if victim:
            victim_val = PIECE_VALUES.get(victim.piece_type, 0)
            attacker_val = PIECE_VALUES.get(attacker.piece_type, 0) if attacker else 0
            score += 1000000 + victim_val * 10 - attacker_val
        else:
            score += 500000  # En passant

    # Promotions
    if move.promotion:
        promo_value = PIECE_VALUES.get(move.promotion, 0)
        score += 800000 + promo_value

    # Killer moves
    if ply in killer_moves:
        if move in killer_moves[ply]:
            score += 90000

    # History heuristic
    hist_key = (move.from_square, move.to_square)
    if hist_key in history_table:
        score += min(history_table[hist_key], 80000)

    # Checks
    board.push(move)
    if board.is_check():
        score += 40000
    board.pop()

    return score

def order_moves(board, depth, ply, hash_move=None):
    """Order moves for better alpha-beta pruning."""
    moves = list(board.legal_moves)
    scored = []

    for move in moves:
        if hash_move and move == hash_move:
            scored.append((move, 10000000))  # Hash move always first
        else:
            scored.append((move, get_move_score(board, move, depth, ply)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [m for m, s in scored]

# =============================================================================
# QUIESCENCE SEARCH (resolve captures at leaf nodes)
# =============================================================================

Q_DELTA = 900  # Queen value - safety margin for standing pat

def quiescence_search(board, alpha, beta, depth=0):
    """Search only captures and checks to resolve tactical sequences."""
    stand_pat = evaluate(board)

    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

    # Delta pruning - if even capturing a queen doesn't help, prune
    if stand_pat + Q_DELTA < alpha:
        return alpha

    # Generate captures only
    captures = [m for m in board.legal_moves if board.is_capture(m)]

    # Also include checks (but limit depth to avoid explosion)
    if depth < 2:
        checks = []
        for m in board.legal_moves:
            if m not in captures:
                board.push(m)
                if board.is_check():
                    checks.append(m)
                board.pop()
        captures.extend(checks)

    # Order captures by MVV-LVA
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

# =============================================================================
# MAIN SEARCH (Alpha-Beta with all optimizations)
# =============================================================================

NODES_SEARCHED = 0
START_TIME = 0
TIME_LIMIT = 0

def should_stop():
    """Check if we've exceeded time limit."""
    if TIME_LIMIT > 0 and time.time() - START_TIME > TIME_LIMIT:
        return True
    return False

def search(board, max_depth, time_limit=0):
    """Iterative deepening search with time limit."""
    global NODES_SEARCHED, START_TIME, TIME_LIMIT, tt

    NODES_SEARCHED = 0
    START_TIME = time.time()
    TIME_LIMIT = time_limit

    clear_search_data()

    # Check opening book first
    fen = board.fen().split(" ")[0] + " " + board.fen().split(" ")[1] + " " + board.fen().split(" ")[2] + " " + board.fen().split(" ")[3]
    if fen in OPENING_BOOK and len(board.move_stack) < 6:
        moves = OPENING_BOOK[fen]
        legal = [str(m) for m in board.legal_moves]
        valid_moves = [m for m in moves if m in legal]
        if valid_moves:
            return 0, chess.Move.from_uci(random.choice(valid_moves))

    best_move = None
    best_score = 0

    # Iterative deepening
    for depth in range(1, max_depth + 1):
        if should_stop():
            break

        score, move = alpha_beta(board, depth, -99999, 99999, 0)

        if should_stop() and best_move is not None:
            break

        if move:
            best_score = score
            best_move = move

    # Fallback: if no best move found but we have legal moves, pick one
    if best_move is None and board.legal_moves.count() > 0:
        best_move = list(board.legal_moves)[0]

    # Final fallback: if iterative deepening found nothing, do a quick depth-1 search
    if best_move is None:
        score, move = alpha_beta(board, 1, -99999, 99999, 0)
        if move:
            best_move = move
            best_score = score

    # Absolute fallback: random legal move
    if best_move is None and board.legal_moves.count() > 0:
        best_move = list(board.legal_moves)[0]
        best_score = evaluate(board)

    return best_score, best_move

def alpha_beta(board, depth, alpha, beta, ply):
    """Alpha-beta search with all optimizations."""
    global NODES_SEARCHED
    NODES_SEARCHED += 1

    # Time check
    if should_stop():
        return 0, None

    # Draw detection
    if board.is_game_over():
        if board.is_checkmate():
            return -99999 + ply if board.turn == chess.WHITE else 99999 - ply, None
        return 0, None

    if board.halfmove_clock >= 100 or board.is_repetition(3):
        return 0, None

    # Transposition table lookup
    hash_key = compute_hash(board)
    tt_entry = tt.get(hash_key)
    hash_move = None
    if tt_entry:
        tt_depth, tt_score, tt_flag, tt_best_move = tt_entry
        if tt_depth >= depth:
            if tt_flag == "EXACT":
                return tt_score, tt_best_move
            elif tt_flag == "LOWER" and tt_score >= beta:
                return tt_score, tt_best_move
            elif tt_flag == "UPPER" and tt_score <= alpha:
                return tt_score, tt_best_move
        if tt_best_move:
            hash_move = tt_best_move

    # Quiescence at leaf nodes
    if depth <= 0:
        score = quiescence_search(board, alpha, beta)
        return score, None

    # Null move pruning (don't prune near mate or in endgame)
    if depth >= 3 and ply > 0 and not board.is_check() and count_material(board) > 2000:
        board.push(chess.Move.null())
        null_score, _ = alpha_beta(board, depth - 1 - 2, -beta, -beta + 1, ply + 1)
        null_score = -null_score
        board.pop()
        if null_score >= beta:
            return beta, None

    # Move ordering
    moves = order_moves(board, depth, ply, hash_move)

    if not moves:
        return evaluate(board), None

    best_move = None
    best_score = -99999 if board.turn == chess.WHITE else 99999

    # Late Move Reduction threshold
    lmr_threshold = 3 if depth >= 3 else 0

    for i, move in enumerate(moves):
        # Late Move Reduction
        reduction = 0
        if i >= lmr_threshold and depth >= 3 and not board.is_capture(move) and not move.promotion and not board.is_check():
            reduction = 1
            if i >= lmr_threshold + 6 and depth >= 4:
                reduction = 2

        board.push(move)

        if reduction > 0:
            # Reduced search
            score, _ = alpha_beta(board, depth - 1 - reduction, -alpha - 1, -alpha, ply + 1)
            score = -score

            # Re-search if promising
            if score > alpha:
                score, _ = alpha_beta(board, depth - 1, -beta, -alpha, ply + 1)
                score = -score
        else:
            # Full search
            score, _ = alpha_beta(board, depth - 1, -beta, -alpha, ply + 1)
            score = -score

        board.pop()

        if should_stop():
            return 0, None

        # Update best
        if board.turn == chess.WHITE:
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, score)
        else:
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, score)

        # Alpha-beta cutoff
        if beta <= alpha:
            # Update killer moves and history
            if not board.is_capture(move):
                if ply not in killer_moves:
                    killer_moves[ply] = [move, None]
                else:
                    killer_moves[ply][1] = killer_moves[ply][0]
                    killer_moves[ply][0] = move

                # History heuristic
                hist_key = (move.from_square, move.to_square)
                history_table[hist_key] = history_table.get(hist_key, 0) + depth * depth

            break

    # Store in transposition table
    if not should_stop() and best_move:
        if best_score <= alpha:
            flag = "UPPER"
        elif best_score >= beta:
            flag = "LOWER"
        else:
            flag = "EXACT"
        tt.store(hash_key, depth, best_score, flag, best_move)

    # Fallback: if no best move found but we have legal moves, pick one
    if best_move is None and board.legal_moves.count() > 0:
        best_move = list(board.legal_moves)[0]

    return best_score, best_move
