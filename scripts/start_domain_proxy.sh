#!/bin/bash
# scripts/start_domain_proxy.sh
# Starts mitmweb on port 8080 (proxy) and port 8081 (web UI) with X-GoogApps-Allowed-Domains injection.

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

# Select Mode (Default to blocked_domain if not specified)
MODE="${1:-blocked_domain}"
if [ -n "$2" ]; then
  export ALLOWED_DOMAIN="$2"
fi

echo "============================================================"
echo " Starting MITMWEB Proxy: Workspace Domain Restriction Test"
echo " Header Injected:  X-GoogApps-Allowed-Domains"
echo "============================================================"
echo " Mode:             $MODE"
echo " Proxy Listening:  http://127.0.0.1:8080"
echo " Web UI Dashboard: http://127.0.0.1:8081"
echo " Target Domain:    ${ALLOWED_DOMAIN:-[Not configured / Using default]}"
echo " Addon Script:     $SCRIPT_DIR/proxy_domain_restriction.py"
echo " Logs:             $REPO_ROOT/proxy_traffic_audit.jsonl"
echo "============================================================"
echo " Available Modes:"
echo "   ./scripts/start_domain_proxy.sh blocked_domain             (Unauthorized domain -> Expected LOGIN BLOCKED)"
echo "   ./scripts/start_domain_proxy.sh allowed_domain [DOMAIN]    (Allowed domain -> Expected LOGIN PERMITTED)"
echo "   ./scripts/start_domain_proxy.sh passthrough                (No headers -> Control baseline)"
echo "============================================================"

# Kill any existing process on port 8080 or 8081
fuser -k 8080/tcp 8081/tcp 2>/dev/null || true

export DOMAIN_RESTRICTION_MODE="$MODE"
"$VENV_DIR/bin/mitmweb" \
  --listen-port 8080 \
  --web-port 8081 \
  --web-host 0.0.0.0 \
  --set block_global=false \
  -s "$SCRIPT_DIR/proxy_domain_restriction.py"
