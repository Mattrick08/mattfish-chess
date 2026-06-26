import csv
import json
import random
import os
import chess
from engine import evaluate

def setup_puzzles(input_file="lichess_db_puzzle.csv", output_file="puzzles.json"):
    """
    Filter Lichess puzzle database:
    - Rating: 1900-3000
    - Minimum 3 full moves (6 half-moves in UCI)
    - At least one puzzle per theme category
    - ONLY puzzles where the side to move is WINNING (positive eval)
    - Store ~500 puzzles max for memory efficiency
    """
    puzzles_by_theme = {}
    all_themes = set()

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found!")
        print("Download from: https://database.lichess.org/lichess_db_puzzle.csv.zst")
        print("Then decompress with: zstd -d lichess_db_puzzle.csv.zst")
        return []

    print("Filtering puzzles... This may take a few minutes.")
    print("Evaluating each position to ensure side to move is winning...")

    with open(input_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rating = int(row['Rating'])
            moves = row['Moves'].split()
            themes = row['Themes'].split()

            # Filter: 1900-3000 rating, 3+ full moves (6+ half-moves)
            if rating < 1900 or rating > 3000:
                continue
            if len(moves) < 6:
                continue

            # Evaluate the position - only keep if side to move is WINNING
            fen = row['FEN']
            try:
                board = chess.Board(fen)
                eval_score = evaluate(board)

                # eval_score is from the perspective of the side to move
                # We want positive eval (winning for side to move)
                # Require at least +1.5 pawns (150 centipawns) advantage
                if eval_score < 150:
                    continue

            except Exception as e:
                continue

            puzzle = {
                'fen': fen,
                'moves': moves,
                'rating': rating,
                'themes': themes,
                'id': row['PuzzleId']
            }

            # Add to each theme bucket
            for theme in themes:
                all_themes.add(theme)
                if theme not in puzzles_by_theme:
                    puzzles_by_theme[theme] = []
                puzzles_by_theme[theme].append(puzzle)

    # Select puzzles: hardest from each theme, up to 3 per theme
    final_puzzles = []
    for theme in sorted(all_themes):
        puzzles = puzzles_by_theme[theme]
        # Sort by rating descending (hardest first)
        puzzles.sort(key=lambda x: x['rating'], reverse=True)
        # Take top 3 from each theme
        count = min(3, len(puzzles))
        selected = puzzles[:count]
        final_puzzles.extend(selected)

    # Shuffle for randomness
    random.shuffle(final_puzzles)

    # Cap at 1000 puzzles to keep file size reasonable
    final_puzzles = final_puzzles[:1000]

    with open(output_file, 'w') as f:
        json.dump(final_puzzles, f)

    print(f"Generated {len(final_puzzles)} puzzles across {len(all_themes)} themes")
    if final_puzzles:
        print(f"Rating range: {min(p['rating'] for p in final_puzzles)} - {max(p['rating'] for p in final_puzzles)}")
    return final_puzzles

if __name__ == "__main__":
    setup_puzzles()
