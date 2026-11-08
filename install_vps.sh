#!/usr/bin/env bash
set -euo pipefail

echo "========================================================"
echo " Mario Music Bot - Automated 24/7 Linux VPS Installer"
echo "========================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SUDO=""
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
  if sudo -n true 2>/dev/null || [ -t 0 ]; then
    SUDO="sudo"
  fi
fi

if command -v apt-get >/dev/null 2>&1 && { [ "$(id -u)" -eq 0 ] || [ -n "$SUDO" ]; }; then
  echo "[1/4] Installing Ubuntu/Debian/Codespaces packages (Python, FFmpeg, Build Tools)..."
  export DEBIAN_FRONTEND=noninteractive
  # Clean up broken third-party Yarn repo if present on cloud/Codespaces images
  $SUDO rm -f /etc/apt/sources.list.d/yarn.list 2>/dev/null || true
  $SUDO apt-get update -y || true
  NODE_PKG="nodejs"
  if command -v node >/dev/null 2>&1; then
    NODE_PKG=""
  fi
  $SUDO apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv python3-dev \
    ffmpeg $NODE_PKG curl unzip gcc libffi-dev libssl-dev || \
  $SUDO apt-get install -y python3 python3-pip python3-venv ffmpeg curl unzip || true
elif command -v pkg >/dev/null 2>&1; then
  echo "[1/4] Installing Android Termux packages..."
  pkg update -y && pkg install -y python ffmpeg nodejs-lts curl unzip clang libffi openssl
else
  echo "[1/4] Rootless environment detected — using built-in Python binary bootstrap."
fi

echo "[2/4] Setting up Python 3.10/3.11 virtual environment (required for py-tgcalls wheels)..."
BASE_PY=""
for candidate in \
  python3.11 \
  python3.10 \
  /opt/python/3.11*/bin/python3 \
  /opt/python/3.10*/bin/python3 \
  /usr/local/python/3.11*/bin/python3 \
  /usr/local/python/3.10*/bin/python3 \
  python3.9 \
  python3; do
  if command -v "$candidate" >/dev/null 2>&1 || [ -x "$candidate" ]; then
    PY_VER="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "")"
    case "$PY_VER" in
      3.9|3.10|3.11)
        BASE_PY="$candidate"
        break
        ;;
    esac
  fi
done

PY_BIN=""
PIP_BIN=""
if [ -n "$BASE_PY" ] && "$BASE_PY" -m venv .venv 2>/dev/null; then
  PY_BIN="$SCRIPT_DIR/.venv/bin/python"
  PIP_BIN="$SCRIPT_DIR/.venv/bin/pip"
elif [ -z "$BASE_PY" ]; then
  echo "[2/4] Host Python is 3.12+; fetching standalone Python 3.11 via uv..."
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  fi
  rm -rf .venv
  uv venv --python 3.11 --seed .venv
  PY_BIN="$SCRIPT_DIR/.venv/bin/python"
  PIP_BIN="$SCRIPT_DIR/.venv/bin/pip"
else
  PY_BIN="$(command -v "$BASE_PY")"
  PIP_BIN="$PY_BIN -m pip"
fi

echo "[3/4] Installing Python dependencies..."
$PIP_BIN install --no-cache-dir -U pip setuptools wheel
$PIP_BIN install --no-cache-dir -r requirements.txt

echo "[4/4] Configuring 24/7 background service..."
if command -v systemctl >/dev/null 2>&1 && [ -d /run/systemd/system ] && { [ "$(id -u)" -eq 0 ] || [ -n "$SUDO" ]; }; then
  SERVICE_FILE="/etc/systemd/system/mario-music.service"
  $SUDO tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=Mario Telegram Group Voice Music Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$SCRIPT_DIR
ExecStart=$PY_BIN -u $SCRIPT_DIR/main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
  $SUDO systemctl daemon-reload
  $SUDO systemctl enable mario-music.service
  $SUDO systemctl restart mario-music.service
  sleep 3
  echo "========================================================"
  echo " Mario Music Bot (@marioxnmusic_bot) is LIVE 24/7!"
  echo " Service status : sudo systemctl status mario-music"
  echo " Live logs      : sudo journalctl -u mario-music -f"
  echo " Restart bot    : sudo systemctl restart mario-music"
  echo "========================================================"
  $SUDO journalctl -u mario-music -n 20 --no-pager || true
else
  pkill -f "$SCRIPT_DIR/run_forever.sh" 2>/dev/null || true
  pkill -f "$SCRIPT_DIR/main.py" 2>/dev/null || true
  rm -f "$SCRIPT_DIR/forever.pid"
  cat > "$SCRIPT_DIR/run_forever.sh" <<EOF
#!/usr/bin/env bash
PIDFILE="$SCRIPT_DIR/forever.pid"
if [ -f "\$PIDFILE" ] && kill -0 "\$(cat "\$PIDFILE" 2>/dev/null)" 2>/dev/null; then
  exit 0
fi
echo \$\$ > "\$PIDFILE"
cd "$SCRIPT_DIR"
while true; do
  "$PY_BIN" -u "$SCRIPT_DIR/main.py" >> "$SCRIPT_DIR/bot.log" 2>&1
  sleep 5
done
EOF
  chmod +x "$SCRIPT_DIR/run_forever.sh"

  if [ -f "$HOME/.bashrc" ] && ! grep -q "mario-music-autoresume" "$HOME/.bashrc" 2>/dev/null; then
    cat >> "$HOME/.bashrc" <<EOF

# mario-music-autoresume
if [ -x "$SCRIPT_DIR/run_forever.sh" ]; then
  nohup bash "$SCRIPT_DIR/run_forever.sh" >/dev/null 2>&1 &
fi
EOF
  fi

  : > "$SCRIPT_DIR/bot.log"
  nohup bash "$SCRIPT_DIR/run_forever.sh" >/dev/null 2>&1 &
  BOT_PID=$!
  sleep 4
  echo "========================================================"
  echo " Mario Music Bot (@marioxnmusic_bot) started 24/7 (PID: $BOT_PID)"
  echo " Live logs: tail -f $SCRIPT_DIR/bot.log"
  echo "========================================================"
  tail -n 20 "$SCRIPT_DIR/bot.log" || true
fi
