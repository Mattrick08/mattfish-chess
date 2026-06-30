#!/usr/bin/env bash
# Render build script: installs Python deps, then tries to download a
# precompiled Stockfish binary. If anything about the download fails,
# the script still exits 0 so the deploy succeeds and the app falls
# back to its built-in Python engine (see app.py: init_stockfish()).
set -u

echo "==> Installing Python dependencies"
pip install -r requirements.txt

STOCKFISH_VERSION="sf_17.1"
BASE_URL="https://github.com/official-stockfish/Stockfish/releases/download/${STOCKFISH_VERSION}"
WORKDIR="$(mktemp -d)"

echo "==> Attempting to download Stockfish ${STOCKFISH_VERSION}"

download_ok=0
for ASSET in "stockfish-ubuntu-x86-64-avx2.tar" "stockfish-ubuntu-x86-64-sse41-popcnt.tar" "stockfish-ubuntu-x86-64.tar"; do
    echo "    trying ${ASSET}..."
    if curl -fsSL -o "${WORKDIR}/stockfish.tar" "${BASE_URL}/${ASSET}"; then
        download_ok=1
        echo "    got ${ASSET}"
        break
    fi
done

if [ "$download_ok" -eq 1 ]; then
    tar -xf "${WORKDIR}/stockfish.tar" -C "${WORKDIR}" || true
    BIN="$(find "${WORKDIR}" -type f -iname 'stockfish-ubuntu-x86-64*' | head -n1)"
    if [ -z "$BIN" ]; then
        BIN="$(find "${WORKDIR}" -type f -iname 'stockfish*' ! -name '*.tar' ! -name '*.nnue' | head -n1)"
    fi
    if [ -n "$BIN" ]; then
        cp "$BIN" ./stockfish
        chmod +x ./stockfish
        echo "==> Stockfish installed at $(pwd)/stockfish"
    else
        echo "==> WARNING: downloaded archive but could not locate the binary inside it. Falling back to built-in engine."
    fi
else
    echo "==> WARNING: could not download a Stockfish binary. Falling back to built-in engine."
fi

rm -rf "${WORKDIR}"
exit 0
