import chess

# Piece square tables - bonus points for good positions
PAWN_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
]

KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]

BISHOP_TABLE = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]

ROOK_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0
]

QUEEN_TABLE = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
]

KING_TABLE = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20
]

PIECE_TABLES = {
    chess.PAWN: PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE,
    chess.KING: KING_TABLE
}

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0
}

def get_position_bonus(piece_type, square, color):
    table = PIECE_TABLES[piece_type]
    if color == chess.WHITE:
        index = (7 - chess.square_rank(square)) * 8 + chess.square_file(square)
    else:
        index = chess.square_rank(square) * 8 + chess.square_file(square)
    return table[index]

def evaluate(board):
    # Check for checkmate
    if board.is_checkmate():
        if board.turn == chess.WHITE:
            return -9999
        else:
            return 9999

    # Check for stalemate (no legal moves but not in check)
    if board.is_stalemate():
        return 0

    # Check for insufficient material
    if board.is_insufficient_material():
        return 0

    # Check for 50-move rule (100 half-moves = 50 full moves)
    if board.halfmove_clock >= 100:
        return 0

    # Check for threefold repetition
    if board.is_repetition(3):
        return 0

    # Check for fivefold repetition (automatic draw)
    if board.is_repetition(5):
        return 0

    score = 0

    for piece_type in PIECE_VALUES:
        for square in board.pieces(piece_type, chess.WHITE):
            score += PIECE_VALUES[piece_type]
            score += get_position_bonus(piece_type, square, chess.WHITE)
        for square in board.pieces(piece_type, chess.BLACK):
            score -= PIECE_VALUES[piece_type]
            score -= get_position_bonus(piece_type, square, chess.BLACK)

    return score

def order_moves(board):
    """Order moves to improve alpha-beta pruning - captures and checks first."""
    moves = list(board.legal_moves)
    def move_score(move):
        score = 0
        # Prioritize captures (MVV-LVA: Most Valuable Victim - Least Valuable Attacker)
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if victim:
                victim_val = PIECE_VALUES.get(victim.piece_type, 0)
                attacker_val = PIECE_VALUES.get(attacker.piece_type, 0) if attacker else 0
                score += 10000 + victim_val - attacker_val
            else:
                score += 5000  # En passant
        # Prioritize checks
        board.push(move)
        if board.is_check():
            score += 2000
        board.pop()
        # Prioritize promotions
        if move.promotion:
            score += 8000
        return score
    return sorted(moves, key=move_score, reverse=True)

def search(board, depth, alpha=-99999, beta=99999):
    # Check for draw conditions at the root
    if depth == 0 or board.is_game_over():
        return evaluate(board), None

    # Check for 50-move rule and repetition during search
    if board.halfmove_clock >= 100 or board.is_repetition(3):
        return 0, None

    best_move = None
    moves = order_moves(board)

    if board.turn == chess.WHITE:
        best_score = -99999
        for move in moves:
            board.push(move)
            score, _ = search(board, depth - 1, alpha, beta)
            board.pop()
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)
            if beta <= alpha:
                break  # Beta cutoff
    else:
        best_score = 99999
        for move in moves:
            board.push(move)
            score, _ = search(board, depth - 1, alpha, beta)
            board.pop()
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            if beta <= alpha:
                break  # Alpha cutoff

    return best_score, best_move
