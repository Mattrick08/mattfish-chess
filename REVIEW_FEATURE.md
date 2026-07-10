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
  (depth 10/14/18 depending on what you pick — Fast/Normal/Precise), running
  with multiple threads and a bigger hash table for stronger, faster search.
- **Move classification**: based on the *drop in win probability* caused by
  the move (the same approach Lichess's own classifier uses), not raw
  centipawn loss. Raw-cp thresholds mis-tag moves in already-decided
  positions — going from +900cp to +700cp barely changes who's winning, so
  it isn't really a blunder even though the cp swing looks large. Win% drop
  scales correctly regardless of how lopsided the position already is.
  Thresholds: Best (matches engine's top choice) · Book (small loss in the
  first 5 moves) · Excellent (<2% win-prob drop) · Good (<5%) · Inaccuracy
  (<10%) · Mistake (<20%) · Blunder (20%+). There's also a mate-aware
  override: letting a forced mate slip away entirely, or mating slower than
  the best line, is always flagged (win% saturates near 0/100 once a mate is
  on the board, which would otherwise hide a real error).
- **Accuracy %**: uses the same win%-based formula Lichess publishes
  (centipawn → win probability via a logistic curve, then accuracy from the
  drop in win probability per move), averaged per side. It's a simplified
  version of Lichess's own method (they additionally weight by a
  game-phase-aware "volatility" factor) — close enough to be meaningful, not
  claimed to be bit-for-bit identical to lichess.org's own number.

## Performance notes
- The engine gets extra threads (up to 4, capped by the host's CPU count)
  and a 128MB hash table on startup, instead of Stockfish's slow defaults of
  1 thread / 16MB — this alone meaningfully speeds up deeper searches.
- Every review has a total wall-clock time budget (`REVIEW_TIME_BUDGET_SECONDS`,
  default 150s), split evenly across every position that needs scoring. Short
  games get generous time per position (searches usually finish well before
  the cap anyway); long games automatically get a smaller per-position slice
  so the whole review still lands inside the budget instead of timing out
  the HTTP request. This is what makes "Precise" (depth 18) reliably finish
  instead of occasionally blowing past gunicorn's `--timeout` on long games.
  The `Procfile` timeout has been bumped to 200s to give this room to breathe.
- If a review ever still feels too slow for your hosting plan, lower
  `REVIEW_DEPTH` and/or `REVIEW_TIME_BUDGET_SECONDS` via environment
  variables: Render → Environment → add `REVIEW_DEPTH=10` or
  `REVIEW_TIME_BUDGET_SECONDS=90`.

## Testing locally
```
pip install -r requirements.txt
./build.sh          # downloads Stockfish into ./bin
python3 app.py
```
Then open `http://localhost:5000/review`.
