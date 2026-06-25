import chess
import time
import random
import math

# ============================================================
# MATT FISH CHESS ENGINE v2.0 - SIGNIFICANTLY STRONGER
# ============================================================
# Features:
# - Transposition Table (128MB)
# - Iterative Deepening
# - Principal Variation Search (PVS)
# - Null Move Pruning
# - Late Move Reduction (LMR)
# - Killer Moves & History Heuristics
# - Enhanced Evaluation (mobility, piece activity, pawn structure)
# - Quiescence Search with delta pruning
# - Aspiration Windows
# - Check extensions
# - Opening book (expanded)
# ============================================================

# ========== PIECE-SQUARE TABLES (tuned for stronger play) ==========

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

# ========== TRANSPOSITION TABLE ==========

class TranspositionTable:
    """Hash table to store previously evaluated positions."""

    def __init__(self, size_mb=128):
        self.size = (size_mb * 1024 * 1024) // 32
        self.table = {}
        self.hits = 0

    def _hash(self, board):
        return board.fen().split()[0] + board.fen().split()[1]

    def lookup(self, board, depth, alpha, beta):
        key = self._hash(board)
        if key in self.table:
            entry = self.table[key]
            if entry['depth'] >= depth:
                self.hits += 1
                if entry['flag'] == 'EXACT':
                    return entry['score'], entry['move']
                elif entry['flag'] == 'LOWER' and entry['score'] >= beta:
                    return entry['score'], entry['move']
                elif entry['flag'] == 'UPPER' and entry['score'] <= alpha:
                    return entry['score'], entry['move']
        return None, None

    def store(self, board, depth, score, flag, move):
        key = self._hash(board)
        if len(self.table) >= self.size:
            keys = list(self.table.keys())
            for k in keys[:len(keys)//4]:
                del self.table[k]
        self.table[key] = {
            'depth': depth,
            'score': score,
            'flag': flag,
            'move': move
        }

# Global transposition table
tt = TranspositionTable(size_mb=128)

# ========== OPENING BOOK (expanded) ==========

OPENING_BOOK = {
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -": ["e2e4", "d2d4", "c2c4", "g1f3"],
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq -": ["e7e5", "c7c5", "e7e6", "c7c6", "d7d6", "g7g6"],
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": ["g1f3", "f1c4", "b1c3"],
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq -": ["b8c6", "g8f6", "d7d6"],
    "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq -": ["f1b5", "f1c4", "b1c3", "d2d4"],
    "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq -": ["a7a6", "g8f6", "f7f5"],
    "r1bqkbnr/1ppp1ppp/p1n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq -": ["b5a4", "b5c6", "b5c4"],
    "r1bqkbnr/1ppp1ppp/p1n5/4p3/B3P3/5N2/PPPP1PPP/RNBQK2R b KQkq -": ["g8f6", "b7b5", "f7f5"],
    "r1bqkb1r/1ppp1ppp/p1n2n2/4p3/B3P3/5N2/PPPP1PPP/RNBQK2R w KQkq -": ["e1g1", "d2d3", "b1c3"],
    "r1bqkb1r/1ppp1ppp/p1n2n2/4p3/B3P3/5N2/PPPP1PPP/RNBQ1RK1 b - -": ["b7b5", "f8e7", "d7d6"],
    "r1bqk2r/pppp1ppp/2n2n2/4p3/1PB1P3/5N2/P1PP1PPP/RNBQ1RK1 b - -": ["c6a5", "c6e7", "d7d6"],
    "rnbqkb1r/ppp2ppp/5n2/3pp3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq -": ["d2d4", "e4d5", "b1c3"],
    "rnbqkb1r/ppp2ppp/2n2n2/3pp3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq -": ["d2d4", "e4d5", "b1c3"],
    "r1bqkb1r/pppp1ppp/2n5/8/3Pp3/5N2/PPP2PPP/RNBQK1NR w KQkq -": ["f3d4", "c2c3"],
    "r1bqkb1r/pppp1ppp/2n2n2/8/2BpP3/8/PPP2PPP/RNBQK1NR w KQkq -": ["g1f3", "c2c3", "f2f4"],
    "rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq -": ["f3e5", "d2d4", "b1c3"],
    "rnbqkb1r/pppp1ppp/5n2/4N3/4P3/8/PPPP1PPP/RNBQKB1R b KQkq -": ["d7d6", "f6e4", "b8c6"],
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": ["g1f3", "b1c3", "f2f4", "c2c3"],
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq -": ["d7d6", "e7e6", "b8c6", "g7g6"],
    "rnbqkbnr/pp2pppp/3p4/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq -": ["d2d4", "c2c3", "b1c3"],
    "rnbqkbnr/pp2pppp/3p4/2p5/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq -": ["c5d4", "g7g6", "b8c6"],
    "rnbqkbnr/pp2pppp/3p4/8/3Pp3/5N2/PPP2PPP/RNBQKB1R w KQkq -": ["f3d4", "c2c3"],
    "rnbqkb1r/pp2pppp/3p1n2/8/3NP3/8/PPP2PPP/RNBQKB1R b KQkq -": ["g8f6", "f8f5", "b8d7"],
    "r1bqkb1r/pp2pppp/2p2n2/8/3PN3/8/PPP2PPP/R1BQKBNR b KQkq -": ["g8f6", "f8f5", "b8d7"],
    "r1bqkb1r/pp2pppp/2p2n2/8/3PN3/5N2/PPP2PPP/R1BQKB1R b KQkq -": ["e7e6", "f8e7", "d7f6"],
    "rn1qkb1r/pp2pppp/2p2n2/5b2/3PN3/5N2/PPP2PPP/R1BQKB1R w KQkq -": ["f3d4", "f3g5", "f1d3"],
    "rn1qkb1r/pp2pppp/2p3b1/8/3P4/6N1/PPP2PPP/R1BQKB1R w KQkq -": ["f1c4", "h2h4", "g1f3"],
    "rnbqkb1r/pp2pppp/2p2n2/8/3PN3/8/PPP2PPP/R1BQKBNR w KQkq -": ["e4f6", "e4g3", "f1d3"],
    "rnbqkbnr/pp2pppp/2p5/3P4/3P4/8/PPP2PPP/RNBQKBNR b KQkq -": ["c6d5", "d8d5", "e6e6"],
    "rnbqkbnr/pp2pppp/2p5/3p4/3P4/8/PPP2PPP/RNBQKBNR w KQkq -": ["g1f3", "b1c3", "f1d3"],
    "rnbqkbnr/pp2pppp/2p5/3pP3/3P4/8/PPP2PPP/RNBQKBNR b KQkq -": ["c8f5", "g8f6", "e7e6"],
    "rnbqkbnr/pp2pppp/2p5/3pP3/3P1b2/8/PPP2PPP/RNBQKBNR w KQkq -": ["b1c3", "f1e2", "g1f3"],
    "rnbqkbnr/pp2pppp/2p5/3pP3/3P1b2/2N5/PPP2PPP/R1BQKBNR b KQkq -": ["e7e6", "g8f6", "b8d7"],
    "rnbqkbnr/pp3ppp/2p1p3/3pP3/3P1b2/2N5/PPP2PPP/R1BQKBNR w KQkq -": ["g1e2", "f1e2", "c1e3"],
    "rnbqkb1r/pppn1ppp/4p3/3pP3/3P4/2N5/PPP2PPP/R1BQKBNR w KQkq -": ["f1d3", "g1f3", "c2c4"],
    "rnbqkbnr/ppp1pppp/3p4/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": ["d2d4", "d2d3", "g1f3"],
    "rnbqkbnr/ppp1pppp/3p4/8/3PP3/8/PPP2PPP/RNBQKBNR b KQkq -": ["g8f6", "g7g6", "e7e5"],
    "rnbqkb1r/ppp1pppp/3p1n2/8/3PP3/8/PPP2PPP/RNBQKBNR w KQkq -": ["b1c3", "g1f3", "f1d3"],
    "rnbqkb1r/ppp1pppp/3p1n2/8/3PP3/2N5/PPP2PPP/R1BQKBNR b KQkq -": ["g7g6", "e7e5", "b8d7"],
    "rnbqkb1r/ppp1pp1p/3p1np1/8/3PP3/2N5/PPP2PPP/R1BQKBNR w KQkq -": ["f1e2", "f1c4", "g1f3"],
    "rnbqk2r/ppp1ppbp/3p1np1/8/3PPP2/2N5/PPP3PP/R1BQKBNR w KQkq -": ["f1c4", "g1f3", "f4f5"],
    "rnbqk2r/ppp1ppbp/3p1np1/8/2BPPP2/2N5/PPP3PP/R1BQK1NR b KQkq -": ["e8g8", "b8c6", "c7c5"],
    "rnbqkbnr/ppp1pp1p/3p2p1/8/3PP3/8/PPP2PPP/RNBQKBNR w KQkq -": ["b1c3", "g1f3", "f1c4"],
    "rnbqkbnr/ppp1pp1p/3p2p1/8/3PP3/2N5/PPP2PPP/R1BQKBNR b KQkq -": ["f8g7", "g8f6", "c7c5"],
    "rnbqk2r/ppp1ppbp/3p2p1/8/3PP3/2N5/PPP2PPP/R1BQKBNR w KQkq -": ["f1c4", "g1f3", "c1e3"],
    "rnbqk2r/ppp1ppbp/3p2p1/8/2BPP3/2N5/PPP2PPP/R1BQK1NR b KQkq -": ["g8f6", "c7c5", "b8c6"],
    "rnbqkb1r/pppppppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": ["e4e5", "b1c3", "d2d4"],
    "rnbqkb1r/pppppppp/5n2/4P3/8/8/PPPP1PPP/RNBQKBNR b KQkq -": ["f6d5", "f6g8", "d7d6"],
    "rnbqkb1r/pppppppp/8/3nP3/8/8/PPPP1PPP/RNBQKBNR w KQkq -": ["d2d4", "c2c4", "g1f3"],
    "rnbqkb1r/pppppppp/8/3nP3/3P4/8/PPP2PPP/RNBQKBNR b KQkq -": ["d7d6", "g7g6", "e7e6"],
    "rnbqkb1r/ppp1pppp/3p4/3nP3/3P4/8/PPP2PPP/RNBQKBNR w KQkq -": ["c2c4", "g1f3", "b1c3"],
    "rnbqkb1r/pppppppp/1n6/4P3/2P5/8/PP1P1PPP/RNBQKBNR b KQkq -": ["d7d6", "e7e6", "g7g6"],
    "rnbqkbnr/pppppppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": ["e4d5", "b1c3", "g1f3"],
    "rnbqkbnr/pppppppp/8/3P4/8/8/PPPP1PPP/RNBQKBNR b KQkq -": ["d8d5", "g8f6", "f8g4"],
    "rnb1kbnr/pppppppp/8/3q4/8/8/PPPP1PPP/RNBQKBNR w KQkq -": ["b1c3", "g1f3", "d2d4"],
    "rnb1kbnr/pppppppp/8/3q4/8/2N5/PPPP1PPP/R1BQKBNR b KQkq -": ["d5a5", "d5d6", "d5d8"],
    "rnb1kbnr/pppppppp/8/q7/8/2N5/PPPP1PPP/R1BQKBNR w KQkq -": ["d2d4", "g1f3", "f1c4"],
    "rnb1kbnr/pppppppp/8/q7/3P4/2N5/PPP2PPP/R1BQKBNR b KQkq -": ["g8f6", "e7e5", "c7c6"],
    "rnbqkb1r/pppppppp/5n2/3p4/8/2N5/PPPP1PPP/R1BQKBNR w KQkq -": ["d2d4", "c2c4", "b1c3"],
    "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq -": ["d7d5", "g8f6", "e7e6", "c7c5", "f7f5"],
    "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq -": ["c2c4", "g1f3", "b1c3"],
    "rnbqkbnr/ppp2ppp/4p3/3p4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq -": ["b1c3", "g1f3", "c1f4"],
    "rnbqkb1r/ppp2ppp/4pn2/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq -": ["c1g5", "g1f3", "e2e3"],
    "rnbqkb1r/ppp2ppp/4pn2/3p2B1/2PP4/2N5/PP2PPPP/R2QKBNR b KQkq -": ["f8e7", "h7h6", "b8d7"],
    "rnbq1rk1/ppp2ppp/4pn2/3p2B1/2PP4/2N2N2/PP2PPPP/R2QKB1R b - -": ["h7h6", "b8d7", "c7c6"],
    "rnbq1rk1/ppp2ppp/4pn2/3p2b1/2PP4/2N2N2/PP2PPPP/R2QKB1R w - -": ["c1e3", "h2h3", "a2a3"],
    "rnbq1rk1/pp3ppp/4pn2/2pp2b1/2PP4/2N2N2/PP2PPPP/R2QKB1R w - -": ["c4d5", "d1c2", "a2a3"],
    "rnbqkbnr/pp2pppp/2p5/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq -": ["e2e3", "g1f3", "c1f4"],
    "rnbqkb1r/pp2pppp/2p2n2/8/2PP4/2N2N2/PP2PPPP/R1BQKB1R b KQkq -": ["e7e6", "d7d5", "f8e7"],
    "rnbqkb1r/pp2pppp/2p2n2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq -": ["c4d5", "g2g3", "e2e3"],
    "rnbqk2r/ppppppbp/5np1/8/2PPP3/2N5/PP3PPP/R1BQKBNR w KQkq -": ["e4e5", "f2f3", "g2g4"],
    "rnbqk2r/ppppppbp/5np1/8/2PPP3/2N2N2/PP3PPP/R1BQKB1R b KQkq -": ["e8g8", "d7d6", "f6e8"],
    "rnbq1rk1/ppppppbp/5np1/8/2PPP3/2N2N2/PP3PPP/R1BQKB1R w - -": ["f1e2", "c1f4", "h2h3"],
    "rnbqk2r/ppppppbp/5np1/8/2PP4/2N2N2/PP2PPPP/R1BQKB1R b KQkq -": ["d7d5", "e8g8", "c7c6"],
    "rnbqk2r/pppp1ppp/4pn2/8/1bPP4/2N5/PP2PPPP/R1BQKBNR w KQkq -": ["d1c2", "c1d2", "a2a3"],
    "rnbqk2r/pppp1ppp/4pn2/8/2PP4/2N5/PP2PPPP/R1BQKBNR b KQkq -": ["b4c3", "d7d5", "e8g8"],
    "rnbqk2r/p1pp1ppp/1p2pn2/8/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq -": ["g2g3", "e2e3", "b2b3"],
    "rnbqkb1r/pppp1ppp/4pn2/8/2P5/2N2N2/PP1PPPPP/R1BQKB1R b KQkq -": ["f8b4", "e7e5", "d7d5"],
    "rnbqk2r/pppp1ppp/4pn2/8/2PP4/6P1/PP2PP1P/RNBQKB1R b KQkq -": ["e8g8", "d7d5", "b7b6"],
    "rnbqkb1r/pp1p1ppp/4pn2/2pP4/2P5/2N5/PP2PPPP/R1BQKBNR b KQkq -": ["e6d5", "b7b5", "g7g6"],
    "rnbqkb1r/ppppp2p/5np1/5p2/3P4/5NP1/PPP1PP1P/RNBQKB1R b KQkq -": ["g7g6", "e7e6", "f8g7"],
    "rnbqkb1r/pppppppp/5n2/8/8/5NP1/PPPPPP1P/RNBQKB1R b KQkq -": ["e7e6", "d7d5", "g7g6"],
    "rnbqkbnr/pp2pppp/2p5/8/3Pp3/2N5/PPP2PPP/R1BQKBNR w KQkq -": ["c3e4", "f1c4", "g1f3"],
    "rnbqkb1r/pppppppp/1n6/4P3/2P5/8/PP1P1PPP/RNBQKBNR b KQkq -": ["d7d6", "e7e6", "g7g6"],
    "rnbqkbnr/ppp2ppp/8/3p4/3P4/2N5/PPP2PPP/R1BQKBNR w KQkq -": ["g1f3", "c1f4", "e2e4"],
}

# ========== SEARCH DATA STRUCTURES ==========

killer_moves = {}
history_table = {}
eval_cache = {}


def clear_search_data():
    killer_moves.clear()
    history_table.clear()


# ========== EVALUATION FUNCTIONS ==========

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
    """Evaluate piece mobility - more mobile pieces are better."""
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
    """Evaluate piece activity and coordination."""
    score = 0

    # Bishop pair bonus
    white_bishops = len(board.pieces(chess.BISHOP, chess.WHITE))
    black_bishops = len(board.pieces(chess.BISHOP, chess.BLACK))
    if white_bishops >= 2:
        score += 30
    if black_bishops >= 2:
        score -= 30

    # Rook on open/semi-open files
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

    # Knight outposts
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
    """Complete position evaluation."""
    fen_key = board.fen().split()[0] + board.fen().split()[1]
    if fen_key in eval_cache:
        return eval_cache[fen_key]

    if board.is_checkmate():
        if board.turn == chess.WHITE:
            return -99999
        else:
            return 99999
    if board.is_stalemate() or board.is_insufficient_material() or board.halfmove_clock >= 100 or board.is_repetition(3):
        return 0

    score = 0
    endgame = is_endgame(board)

    # Material and piece-square tables
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

    # Tempo bonus
    if board.turn == chess.WHITE:
        score += 10
    else:
        score -= 10

    eval_cache[fen_key] = score
    return score


# ========== MOVE ORDERING ==========

def get_move_score(board, move, depth, ply):
    score = 0

    # Transposition table move
    cached_score, cached_move = tt.lookup(board, depth, -99999, 99999)
    if cached_move and move == cached_move:
        score += 10000000

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

NODES_SEARCHED = 0
START_TIME = 0
TIME_LIMIT = 0


def should_stop():
    if TIME_LIMIT > 0 and time.time() - START_TIME > TIME_LIMIT:
        return True
    return False


def iterative_deepening(board, max_depth, time_limit):
    """Iterative deepening with time management."""
    global NODES_SEARCHED, START_TIME, TIME_LIMIT
    NODES_SEARCHED = 0
    START_TIME = time.time()
    TIME_LIMIT = time_limit
    clear_search_data()

    # Check opening book
    parts = board.fen().split()
    key = ' '.join(parts[:4])
    if key in OPENING_BOOK and len(board.move_stack) < 12:
        moves = OPENING_BOOK[key]
        legal = [str(m) for m in board.legal_moves]
        valid = [m for m in moves if m in legal]
        if valid:
            return 0, chess.Move.from_uci(random.choice(valid))

    best_move = None
    best_score = 0

    # Iterative deepening with aspiration windows
    for depth in range(1, max_depth + 1):
        if should_stop() and best_move is not None:
            break

        # Aspiration window (tighter bounds for deeper searches)
        if depth >= 4 and best_move is not None:
            window = 50
            alpha = best_score - window
            beta = best_score + window
            score, move = alpha_beta(board, depth, alpha, beta, 0, True)
            if score <= alpha or score >= beta:
                # Fail-low or fail-high, re-search with full window
                score, move = alpha_beta(board, depth, -99999, 99999, 0, True)
        else:
            score, move = alpha_beta(board, depth, -99999, 99999, 0, True)

        if should_stop() and best_move is not None:
            break

        if move:
            best_score = score
            best_move = move

            # If we found a mate, stop searching
            if abs(best_score) > 90000:
                break

    if best_move is None:
        score, move = alpha_beta(board, 1, -99999, 99999, 0, True)
        if move:
            best_move = move
            best_score = score

    if best_move is None and board.legal_moves.count() > 0:
        best_move = list(board.legal_moves)[0]
        best_score = evaluate(board)

    return best_score, best_move


def alpha_beta(board, depth, alpha, beta, ply, is_root=False):
    """Alpha-beta with PVS, null move pruning, LMR, and TT."""
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

    # Transposition table lookup
    cached_score, cached_move = tt.lookup(board, depth, alpha, beta)
    if cached_score is not None:
        return cached_score, cached_move

    # Check extension
    if board.is_check() and depth < 12:
        depth += 1

    if depth <= 0:
        score = quiescence_search(board, alpha, beta)
        return score, None

    # Null move pruning (don't do at root, in check, or in endgame)
    if not is_root and not board.is_check() and depth >= 3 and not is_endgame(board):
        board.push(chess.Move.null())
        null_score, _ = alpha_beta(board, depth - 1 - 2, -beta, -beta + 1, ply + 1)
        null_score = -null_score
        board.pop()
        if null_score >= beta:
            return beta, None

    moves = order_moves(board, depth, ply, cached_move)
    if not moves:
        return evaluate(board), None

    best_move = None
    best_score = -99999 if board.turn == chess.WHITE else 99999

    # Principal Variation Search (PVS)
    first_move = True
    lmr_threshold = 3 if depth >= 3 else 0

    for i, move in enumerate(moves):
        if should_stop():
            return 0, None

        # Late Move Reduction
        reduction = 0
        if i >= lmr_threshold and depth >= 3 and not board.is_capture(move) and not move.promotion and not board.is_check():
            reduction = 1
            if i >= lmr_threshold + 6 and depth >= 4:
                reduction = 2

        board.push(move)

        if first_move:
            # Full window search for first move (PV move)
            score, _ = alpha_beta(board, depth - 1 - reduction, -beta, -alpha, ply + 1)
            score = -score
        else:
            # Null window search for non-PV moves
            score, _ = alpha_beta(board, depth - 1 - reduction, -alpha - 1, -alpha, ply + 1)
            score = -score
            if score > alpha and score < beta:
                # Re-search with full window if null window fails high
                score, _ = alpha_beta(board, depth - 1 - reduction, -beta, -alpha, ply + 1)
                score = -score

        board.pop()
        first_move = False

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
            # Update killer moves and history
            if not board.is_capture(move):
                if ply not in killer_moves:
                    killer_moves[ply] = [move, None]
                else:
                    killer_moves[ply][1] = killer_moves[ply][0]
                    killer_moves[ply][0] = move
                hist_key = (move.from_square, move.to_square)
                history_table[hist_key] = history_table.get(hist_key, 0) + depth * depth
            break

    # Store in transposition table
    if best_score <= alpha:
        flag = 'UPPER'
    elif best_score >= beta:
        flag = 'LOWER'
    else:
        flag = 'EXACT'
    tt.store(board, depth, best_score, flag, best_move)

    return best_score, best_move


# ========== MAIN SEARCH ENTRY POINT ==========

def search(board, max_depth, time_limit=0):
    """Main search function - wrapper for iterative_deepening."""
    return iterative_deepening(board, max_depth, time_limit)
