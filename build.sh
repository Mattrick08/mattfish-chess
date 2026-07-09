#!/usr/bin/env bash
# Render build script.
# Set this as your Render service's Build Command:  ./build.sh
set -e

echo "==> Installing Python dependencies"
pip install -r requirements.txt

echo "==> Downloading Stockfish (used only for the Game Review feature)"
STOCKFISH_VERSION="sf_17.1"
STOCKFISH_ASSET="stockfish-ubuntu-x86-64.tar"
mkdir -p bin
curl -sL -o bin/stockfish.tar \
  "https://github.com/official-stockfish/Stockfish/releases/download/${STOCKFISH_VERSION}/${STOCKFISH_ASSET}"
tar -xf bin/stockfish.tar -C bin
rm bin/stockfish.tar
chmod +x bin/stockfish/stockfish-ubuntu-x86-64

echo "==> Build complete"
