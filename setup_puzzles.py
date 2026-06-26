import csv
import json
import random
import os
import chess
from engine import evaluate

def setup_puzzles(input_file="lichess_db_puzzle.csv", output_file="puzzles.json"):
    """
    Filter Lichess puzzle database:
    - Rating: ALL ranges (500-3000)
    - Minimum 3 full moves (6 half-moves in UCI)
    - At least one puzzle per theme category
    - ONLY puzzles where the side to move is WINNING (positive eval)
    - Mix of difficulty levels for variety
    """
    puzzles_by_theme = {}
    all_themes = set()

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found!")
        print("Download from: https://database.lichess.org/lichess_db_puzzle.csv.zst")
        print("Then decompress with: zstd -d lichess_db_puzzle.csv.zst")
        return []

    print("Filtering puzzles from ALL rating ranges...")
    print("Evaluating positions to ensure side to move is winning...")

    with open(input_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rating = int(row['Rating'])
            moves = row['Moves'].split()
            themes = row['Themes'].split()

            # Filter: ALL ratings up to 3000, 3+ full moves (6+ half-moves)
            if rating > 3000:
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

    # Select puzzles: mix of difficulties from each theme
    final_puzzles = []
    for theme in sorted(all_themes):
        puzzles = puzzles_by_theme[theme]
        # Sort by rating
        puzzles.sort(key=lambda x: x['rating'])

        # Pick a mix: easy, medium, hard from each theme
        count = min(5, len(puzzles))
        if count >= 5:
            # Pick 5 puzzles spread across difficulty range
            selected = [
                puzzles[0],                    # Easiest
                puzzles[len(puzzles)//4],      # Easy-Medium
                puzzles[len(puzzles)//2],      # Medium
                puzzles[3*len(puzzles)//4],    # Medium-Hard
                puzzles[-1]                     # Hardest
            ]
        else:
            selected = puzzles[:count]

        final_puzzles.extend(selected)

    # Shuffle for randomness
    random.shuffle(final_puzzles)

    # Cap at 1500 puzzles to keep file size reasonable
    final_puzzles = final_puzzles[:1500]

    with open(output_file, 'w') as f:
        json.dump(final_puzzles, f)

    print(f"Generated {len(final_puzzles)} puzzles across {len(all_themes)} themes")
    if final_puzzles:
        print(f"Rating range: {min(p['rating'] for p in final_puzzles)} - {max(p['rating'] for p in final_puzzles)}")
    return final_puzzles

if __name__ == "__main__":
    setup_puzzles()
