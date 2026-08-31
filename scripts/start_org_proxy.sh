#!/bin/bash
# scripts/start_org_proxy.sh
# Starts mitmweb on port 8080 (proxy) and port 8081 (web UI) with X-Goog-Allowed-Resources injection.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"

# Ensure venv exists and has dependencies installed
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating Python virtual environment in $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
  echo "Installing dependencies..."
  "$VENV_DIR/bin/pip" install --upgrade pip
  "$VENV_DIR/bin/pip" install -r "$REPO_ROOT/requirements.txt"
fi

# Select Mode (Default to fake_org if not specified)
MODE="${1:-fake_org}"
if [ -n "$2" ]; then
  export ALLOWED_ORG_ID="$2"
fi

echo "============================================================"
echo " Starting MITMWEB Proxy: GCP Organization Restriction Test"
echo " Header Injected:  X-Goog-Allowed-Resources"
echo "============================================================"
echo " Mode:             $MODE"
echo " Proxy Listening:  http://127.0.0.1:8080"
echo " Web UI Dashboard: http://127.0.0.1:8081"
echo " Target Org ID:    ${ALLOWED_ORG_ID:-[Not configured / Using default]}"
echo " Addon Script:     $SCRIPT_DIR/proxy_org_restriction.py"
echo " Logs:             $REPO_ROOT/proxy_traffic_audit.jsonl"
echo "============================================================"
echo " Available Modes:"
echo "   ./scripts/start_org_proxy.sh fake_org                      (Fake Org -> Expected BLOCKED)"
echo "   ./scripts/start_org_proxy.sh real_org [YOUR_ORG_ID]        (Real Org -> Expected ALLOWED)"
echo "   ./scripts/start_org_proxy.sh foreign_org                   (Foreign Org -> Expected BLOCKED)"
echo "   ./scripts/start_org_proxy.sh passthrough                   (No headers -> Control baseline)"
echo "============================================================"

# Kill any existing process on port 8080 or 8081
fuser -k 8080/tcp 8081/tcp 2>/dev/null || true

export ORG_RESTRICTION_MODE="$MODE"
"$VENV_DIR/bin/mitmweb" \
  --listen-port 8080 \
  --web-port 8081 \
  --web-host 0.0.0.0 \
  --set block_global=false \
  -s "$SCRIPT_DIR/proxy_org_restriction.py"
