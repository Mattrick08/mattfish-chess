import chess
import time
import random

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

    # More Ruy Lopez lines
    "r1bqk2r/2pp1ppp/p1n2n2/1pb1p3/1B2P3/5N2/PPPP1PPP/RNBQR1K1 w - -": ["c2c3", "a2a4", "h2h3"],
    "r1bq1rk1/2pp1ppp/p1n2n2/1pb1p3/1B2P3/5N2/PPPP1PPP/RNBQR1K1 w - -": ["c2c3", "a2a4", "d2d3"],

    # Italian Game lines
    "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 b kq -": ["e8g8", "d7d6", "h7h6"],
    "r1bq1rk1/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 w - -": ["c2c3", "d2d3", "h2h3"],
    "r1bq1rk1/pppp1ppp/2n2n2/4p3/1PB1P3/5N2/P1PP1PPP/RNBQ1RK1 b - -": ["c6a5", "c6e7", "d7d6"],

    # Scotch lines
    "r1bqkb1r/pppp1ppp/2n2n2/8/2BpP3/8/PPP2PPP/RNBQK1NR w KQkq -": ["g1f3", "c2c3", "f2f4"],
    "r1bqkb1r/pppp1ppp/2n2n2/8/2BpP3/5N2/PPP2PPP/RNBQK2R b KQkq -": ["e8g8", "d7d6", "f8e7"],

    # Sicilian - more Najdorf
    "rnbqkb1r/1p3ppp/p2p1n2/4p3/3NP3/2N1P3/PPP2PPP/R1BQKB1R w KQkq -": ["f1d3", "f1e2", "g2g4"],
    "rnbqkb1r/1p3ppp/p2p1n2/4p3/3NP3/2N1P3/PPP2PPP/R1BQKB1R w KQkq -": ["f1d3", "f1e2", "g2g4"],
    "rnbqkb1r/1p3ppp/p2p1n2/4p3/3NP3/2NBPP2/PPP3PP/R1BQK2R b KQkq -": ["e8g8", "b8d7", "c7c5"],

    # Sicilian - Dragon Yugoslav
    "rnbqk2r/pp2ppbp/3p1np1/8/2BpP3/2N2N2/PPP2PPP/R1BQ1RK1 w kq -": ["c1e3", "d2d4", "h2h3"],
    "rnbqk2r/pp2ppbp/3p1np1/8/2BpP3/2N1BN2/PPP2PPP/R2Q1RK1 b kq -": ["e8g8", "b8c6", "d7d5"],

    # French - more lines
    "rnbqkb1r/ppp2ppp/4pn2/3pP3/3P4/2N5/PPP2PPP/R1BQKBNR b KQkq -": ["f6d7", "f6e4", "f6g8"],
    "rnbqkb1r/pppn1ppp/4p3/3pP3/3P4/2N5/PPP2PPP/R1BQKBNR w KQkq -": ["f1d3", "g1f3", "c2c4"],
    "rnbqkb1r/pppn1ppp/4p3/3pP3/3P4/2N2N2/PPP2PPP/R1BQKB1R b KQkq -": ["f8e7", "c7c5", "b8c6"],
    "rnbqk2r/pppn1ppp/4p3/3pP3/1b1P4/2N2N2/PPP2PPP/R1BQKB1R w kq -": ["c1d2", "a2a3", "d1c2"],

    # Caro-Kann - more lines
    "r1bqkb1r/pp1npppp/2p2n2/8/3PN3/8/PPP2PPP/R1BQKBNR w KQkq -": ["g1f3", "f1d3", "f1c4"],
    "r1bqkb1r/pp1npppp/2p2n2/8/3PN3/5N2/PPP2PPP/R1BQKB1R b KQkq -": ["e7e6", "f8e7", "d7f6"],
    "rn1qkb1r/pp2pppp/2p2n2/5b2/3PN3/5N2/PPP2PPP/R1BQKB1R w KQkq -": ["f3d4", "f3g5", "f1d3"],
    "rn1qkb1r/pp2pppp/2p2n2/5b2/3PN3/5N2/PPP2PPP/R1BQKB1R w KQkq -": ["f3d4", "f3g5", "f1d3"],

    # Pirc/Modern
    "rnbqk2r/ppp1ppbp/3p1np1/8/3PPP2/2N5/PPP3PP/R1BQKBNR w KQkq -": ["f1c4", "g1f3", "f4f5"],
    "rnbqk2r/ppp1ppbp/3p1np1/8/2BPPP2/2N5/PPP3PP/R1BQK1NR b KQkq -": ["e8g8", "b8c6", "c7c5"],

    # Queen's Gambit Declined - more lines
    "rnbq1rk1/ppp2ppp/4pn2/3p2B1/2PP4/2N2N2/PP2PPPP/R2QKB1R b - -": ["h7h6", "b8d7", "c7c6"],
    "rnbq1rk1/ppp2ppp/4pn2/3p2b1/2PP4/2N2N2/PP2PPPP/R2QKB1R w - -": ["c1e3", "h2h3", "a2a3"],
    "rnbq1rk1/pp3ppp/4pn2/2pp2b1/2PP4/2N2N2/PP2PPPP/R2QKB1R w - -": ["c4d5", "d1c2", "a2a3"],

    # Slav Defense
    "rnbqkb1r/pp2pppp/2p2n2/8/2PP4/2N2N2/PP2PPPP/R1BQKB1R b KQkq -": ["e7e6", "d7d5", "f8e7"],
    "rnbqkb1r/pp2pppp/2p2n2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq -": ["c4d5", "g2g3", "e2e3"],

    # King's Indian
    "rnbqk2r/ppppppbp/5np1/8/2PPP3/2N5/PP3PPP/R1BQKBNR w KQkq -": ["e4e5", "f2f3", "g2g4"],
    "rnbqk2r/ppppppbp/5np1/8/2PPP3/2N2N2/PP3PPP/R1BQKB1R b KQkq -": ["e8g8", "d7d6", "f6e8"],
    "rnbq1rk1/ppppppbp/5np1/8/2PPP3/2N2N2/PP3PPP/R1BQKB1R w - -": ["f1e2", "c1f4", "h2h3"],

    # Grunfeld
    "rnbqk2r/ppppppbp/5np1/8/2PP4/2N2N2/PP2PPPP/R1BQKB1R b KQkq -": ["d7d5", "e8g8", "c7c6"],
    "rnbqk2r/ppppppbp/5np1/8/2PP4/2N2N2/PP2PPPP/R1BQKB1R b KQkq -": ["d7d5", "e8g8", "c7c6"],

    # Nimzo-Indian
    "rnbqk2r/pppp1ppp/4pn2/8/1bPP4/2N5/PP2PPPP/R1BQKBNR w KQkq -": ["d1c2", "c1d2", "a2a3"],
    "rnbqk2r/pppp1ppp/4pn2/8/2PP4/2N5/PP2PPPP/R1BQKBNR b KQkq -": ["b4c3", "d7d5", "e8g8"],
    "rnbqk2r/pppp1ppp/4pn2/8/2PP4/2N5/PP2PPPP/R1BQKBNR b KQkq -": ["b4c3", "d7d5", "e8g8"],

    # Queen's Indian
    "rnbqk2r/p1pp1ppp/1p2pn2/8/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq -": ["g2g3", "e2e3", "b2b3"],
    "rnbqk2r/p1pp1ppp/1p2pn2/8/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq -": ["g2g3", "e2e3", "b2b3"],

    # English Opening
    "rnbqkb1r/pppp1ppp/4pn2/8/2P5/2N2N2/PP1PPPPP/R1BQKB1R b KQkq -": ["f8b4", "e7e5", "d7d5"],
    "rnbqkb1r/pppp1ppp/4pn2/8/2P5/2N2N2/PP1PPPPP/R1BQKB1R b KQkq -": ["f8b4", "e7e5", "d7d5"],

    # Catalan
    "rnbqk2r/pppp1ppp/4pn2/8/2PP4/6P1/PP2PP1P/RNBQKB1R b KQkq -": ["e8g8", "d7d5", "b7b6"],

    # Benoni
    "rnbqkb1r/pp1p1ppp/4pn2/2pP4/2P5/2N5/PP2PPPP/R1BQKBNR b KQkq -": ["e6d5", "b7b5", "g7g6"],

    # Dutch
    "rnbqkb1r/ppppp2p/5np1/5p2/3P4/5NP1/PPP1PP1P/RNBQKB1R b KQkq -": ["g7g6", "e7e6", "f8g7"],

    # Reti
    "rnbqkb1r/pppppppp/5n2/8/8/5NP1/PPPPPP1P/RNBQKB1R b KQkq -": ["e7e6", "d7d5", "g7g6"],

    # 1.e4 c6 (Caro-Kann) with 2.d4 d5 3.Nc3 dxe4
    "rnbqkbnr/pp2pppp/2p5/8/3Pp3/2N5/PPP2PPP/R1BQKBNR w KQkq -": ["c3e4", "f1c4", "g1f3"],

    # Alekhine 4.c4 Nb6
    "rnbqkb1r/pppppppp/1n6/4P3/2P5/8/PP1P1PPP/RNBQKBNR b KQkq -": ["d7d6", "e7e6", "g7g6"],

    # Scandinavian 3.Nc3 Qd8
    "rnbqkbnr/ppp2ppp/8/3p4/3P4/2N5/PPP2PPP/R1BQKBNR w KQkq -": ["g1f3", "c1f4", "e2e4"],
}

# Programmatically generated opening book from strong theory
OPENING_BOOK = {
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -": ["c2c4"],
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": ["d2d4"],
    "r1bqkbnr/1ppp1ppp/p1n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq -": ["e1g1"],
    "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq -": ["f3d4"],
    "rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq -": ["d2d4"],
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": ["d2d4"],
    "rnbqkbnr/pp2pppp/3p4/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq -": ["f3d4"],
    "rnbqkbnr/pp2pppp/3p4/8/3pP3/5N2/PPP2PPP/RNBQKB1R w KQkq -": ["b1c3"],
    "rnbqkb1r/pp2pppp/3p1n2/8/3NP3/8/PPP2PPP/RNBQKB1R w KQkq -": ["c1e3"],
    "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq -": ["f1d3"],
    "rnbqkb1r/pp2pp1p/3p1np1/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq -": ["f2f3"],
    "r1bqkbnr/pp1ppppp/2n5/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq -": ["f3d4"],
    "r1bqkbnr/pp1ppppp/2n5/8/3pP3/5N2/PPP2PPP/RNBQKB1R w KQkq -": ["b1c3"],
    "rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": ["b1c3"],
    "rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq -": ["e4e5"],
    "rnbqkb1r/ppp2ppp/4pn2/3p4/3PP3/2N5/PPP2PPP/R1BQKBNR w KQkq -": ["f1d3"],
    "rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": ["e4e5"],
    "rnbqkbnr/pp2pppp/2p5/8/3Pp3/2N5/PPP2PPP/R1BQKBNR w KQkq -": ["g1f3"],
    "rnbqkbnr/ppp1pppp/3p4/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": ["b1c3"],
    "rnbqkb1r/ppp1pppp/3p1n2/8/3PP3/8/PPP2PPP/RNBQKBNR w KQkq -": ["f1e2"],
    "rnbqkbnr/ppp1pp1p/3p2p1/8/3PP3/8/PPP2PPP/RNBQKBNR w KQkq -": ["f1e2"],
    "rnbqkb1r/pppppppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": ["d2d4"],
    "rnbqkb1r/pppppppp/8/3nP3/8/8/PPPP1PPP/RNBQKBNR w KQkq -": ["c2c4"],
    "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": ["b1c3"],
    "rnb1kbnr/ppp1pppp/8/3q4/8/8/PPPP1PPP/RNBQKBNR w KQkq -": ["d2d4"],
    "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq -": ["g1f3"],
    "rnbqkbnr/ppp2ppp/4p3/3p4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq -": ["c1g5"],
    "rnbqkbnr/pp2pppp/2p5/3p4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq -": ["b1c3"],
    "rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq -": ["d4d5"],
    "rnbqkb1r/pppp1ppp/4pn2/8/2PP4/8/PP2PPPP/RNBQKBNR w KQkq -": ["c1g5"],
    "rnbqkb1r/pp1ppppp/5n2/2p5/2PP4/8/PP2PPPP/RNBQKBNR w KQkq -": ["b1c3"],
    "rnbqkb1r/pppppp1p/5np1/8/2PP4/8/PP2PPPP/RNBQKBNR w KQkq -": ["g2g3"],
    "rnbqkbnr/pppp1ppp/8/4p3/2P5/8/PP1PPPPP/RNBQKBNR w KQkq -": ["g1f3"],
    "rnbqkbnr/pp1ppppp/8/2p5/2P5/8/PP1PPPPP/RNBQKBNR w KQkq -": ["b1c3"],
    "rnbqkbnr/ppp1pppp/8/3p4/8/5N2/PPPPPPPP/RNBQKB1R w KQkq -": ["b1c3"],
    "rnbqkbnr/ppppp1pp/8/5p2/3P4/8/PPP1PPPP/RNBQKBNR w KQkq -": ["g1f3"],
}

def see(board, square, color):
    """Static Exchange Evaluation - evaluate the outcome of a capture sequence on a square."""
    # Get the least valuable attacker for the given color
    attackers = board.attackers(color, square)
    if not attackers:
        return 0
    
    # Find the least valuable attacker
    min_value = 99999
    best_attacker_sq = None
    for sq in attackers:
        piece = board.piece_at(sq)
        if piece:
            val = PIECE_VALUES.get(piece.piece_type, 0)
            if val < min_value:
                min_value = val
                best_attacker_sq = sq
    
    if best_attacker_sq is None:
        return 0
    
    # Value of the piece on the target square
    victim = board.piece_at(square)
    victim_value = PIECE_VALUES.get(victim.piece_type, 0) if victim else 0
    
    # Make the capture
    move = chess.Move(best_attacker_sq, square)
    if move not in board.legal_moves:
        return 0
    
    board.push(move)
    # Recursively evaluate the opponent's response
    score = victim_value - see(board, square, not color)
    board.pop()
    
    return max(0, score)

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
    """Penalize pieces that are attacked and not defended."""
    score = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.color == color:
            attackers = len(list(board.attackers(not color, square)))
            defenders = len(list(board.attackers(color, square)))
            if attackers > 0:
                piece_val = PIECE_VALUES.get(piece.piece_type, 0)
                if attackers > defenders:
                    # Hanging piece - big penalty
                    score -= piece_val // 2
                elif attackers == defenders:
                    # Traded piece - small penalty
                    score -= piece_val // 8
    return score

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

def evaluate_mobility(board):
    """Simple mobility bonus - count legal moves."""
    # Save state
    turn = board.turn
    white_moves = len(list(board.legal_moves)) if turn == chess.WHITE else 0
    board.turn = chess.BLACK
    black_moves = len(list(board.legal_moves))
    board.turn = chess.WHITE
    white_moves = len(list(board.legal_moves))
    board.turn = turn
    return (white_moves - black_moves) * 2

def evaluate(board):
    if board.is_checkmate():
        if board.turn == chess.WHITE:
            return -99999
        else:
            return 99999
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
    if not endgame:
        score += evaluate_king_safety(board)
    if board.turn == chess.WHITE:
        score += 10
    else:
        score -= 10
    return score

killer_moves = {}
history_table = {}

def clear_search_data():
    killer_moves.clear()
    history_table.clear()

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

NODES_SEARCHED = 0
START_TIME = 0
TIME_LIMIT = 0

def should_stop():
    if TIME_LIMIT > 0 and time.time() - START_TIME > TIME_LIMIT:
        return True
    return False

def search(board, max_depth, time_limit=0):
    global NODES_SEARCHED, START_TIME, TIME_LIMIT
    NODES_SEARCHED = 0
    START_TIME = time.time()
    TIME_LIMIT = time_limit
    clear_search_data()
    # Check opening book
    parts = board.fen().split()
    key = ' '.join(parts[:4])
    if key in OPENING_BOOK and len(board.move_stack) < 10:
        moves = OPENING_BOOK[key]
        legal = [str(m) for m in board.legal_moves]
        valid = [m for m in moves if m in legal]
        if valid:
            return 0, chess.Move.from_uci(random.choice(valid))
    best_move = None
    best_score = 0
    for depth in range(1, max_depth + 1):
        if should_stop():
            break
        score, move = alpha_beta(board, depth, -99999, 99999, 0)
        if should_stop() and best_move is not None:
            break
        if move:
            best_score = score
            best_move = move
    if best_move is None:
        score, move = alpha_beta(board, 1, -99999, 99999, 0)
        if move:
            best_move = move
            best_score = score
    if best_move is None and board.legal_moves.count() > 0:
        best_move = list(board.legal_moves)[0]
        best_score = evaluate(board)
    return best_score, best_move

def alpha_beta(board, depth, alpha, beta, ply):
    global NODES_SEARCHED
    NODES_SEARCHED += 1
    if should_stop():
        return 0, None
    if board.is_game_over():
        if board.is_checkmate():
            return -99999 + ply if board.turn == chess.WHITE else 99999 - ply, None
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
    best_score = -99999 if board.turn == chess.WHITE else 99999
    lmr_threshold = 3 if depth >= 3 else 0
    for i, move in enumerate(moves):
        reduction = 0
        if i >= lmr_threshold and depth >= 3 and not board.is_capture(move) and not move.promotion and not board.is_check():
            reduction = 1
            if i >= lmr_threshold + 6 and depth >= 4:
                reduction = 2
        board.push(move)
        if reduction > 0:
            score, _ = alpha_beta(board, depth - 1 - reduction, -alpha - 1, -alpha, ply + 1)
            score = -score
            if score > alpha:
                score, _ = alpha_beta(board, depth - 1, -beta, -alpha, ply + 1)
                score = -score
        else:
            score, _ = alpha_beta(board, depth - 1, -beta, -alpha, ply + 1)
            score = -score
        board.pop()
        if should_stop():
            return 0, None
        if board.turn == chess.WHITE:
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, score)
        else:
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
        if beta <= alpha:
            if not board.is_capture(move):
                if ply not in killer_moves:
                    killer_moves[ply] = [move, None]
                else:
                    killer_moves[ply][1] = killer_moves[ply][0]
                    killer_moves[ply][0] = move
                hist_key = (move.from_square, move.to_square)
                history_table[hist_key] = history_table.get(hist_key, 0) + depth * depth
            break
    return best_score, best_move
