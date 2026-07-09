# Game Review — Stockfish integration

## What was added
- `analysis_engine.py` — talks to a real Stockfish binary via `python-chess`'s
  UCI interface. Completely separate from `engine.py` (MattFish's own playing
  engine, untouched) — Stockfish is only ever used to *score* positions for
  the review page, never to play moves in a live game.
- `/review` — new page: paste a PGN, pick a depth, get accuracy % for both
  sides, an eval bar, and a move-by-move classification (Best / Excellent /
  Good / Book / Inaccuracy / Mistake / Blunder) with the engine's suggested
  move whenever you didn't play the top choice.
- `/api/review/analyze` — POST endpoint, `{"pgn": "...", "depth": 14}` →
  full analysis JSON.
- `build.sh` — downloads the official Stockfish Linux binary at deploy time.
- A "📊 Review a Game" button on the homepage.

## ⚠️ One manual step on Render
Stockfish's binary is ~80MB — too big to commit to git, so it's fetched
during the build instead. **You need to change your Render service's Build
Command:**

1. Render dashboard → your service → **Settings** → **Build & Deploy**
2. Change **Build Command** from `pip install -r requirements.txt` to:
   ```
   ./build.sh
   ```
3. Save. Trigger a manual deploy (or push a commit — either triggers a rebuild
   with the new command).

That's it — `build.sh` still runs `pip install -r requirements.txt` itself,
it just also grabs the Stockfish binary into `bin/stockfish/` right after.

## How the numbers are computed
- **Evaluation**: every position in the game is scored once by Stockfish
  (depth 10/14/18 depending on what you pick — Fast/Normal/Precise).
- **Move classification**: centipawn loss between the position before and
  after each move (from the mover's perspective). Thresholds: Best (matches
  engine's top choice) · Book (small loss in the first 5 moves) · Excellent
  (<20cp) · Good (<50cp) · Inaccuracy (<100cp) · Mistake (<200cp) · Blunder
  (200cp+).
- **Accuracy %**: uses the same win%-based formula Lichess publishes
  (centipawn → win probability via a logistic curve, then accuracy from the
  drop in win probability per move), averaged per side. It's a simplified
  version of Lichess's own method (they additionally weight by a
  game-phase-aware "volatility" factor) — close enough to be meaningful, not
  claimed to be bit-for-bit identical to lichess.org's own number.

## Performance notes
- Depth 14 (default) takes roughly 0.1–0.4s per position on typical server
  hardware, so a 40-move game (~80 plies) usually finishes in 10–25 seconds.
  Depth 18 ("Precise") is noticeably slower; use it for shorter games.
- The engine process is a single long-lived subprocess reused across
  requests (not restarted every time), which matches the `gunicorn -w 1`
  setup already in your `Procfile`. If you ever scale to multiple workers,
  each worker will start its own Stockfish process — that's fine, no shared
  state needed.
- If a review ever times out on Render's free tier (which has a limited
  request timeout), lower `REVIEW_DEPTH` via an environment variable:
  Render → Environment → add `REVIEW_DEPTH=10`.

## Testing locally
```
pip install -r requirements.txt
./build.sh          # downloads Stockfish into ./bin
python3 app.py
```
Then open `http://localhost:5000/review`.
