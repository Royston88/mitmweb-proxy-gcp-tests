#!/bin/bash
# scripts/launch_chrome.sh
# Launches system Google Chrome configured to route through the local proxy.

PROXY_SERVER="${PROXY_SERVER:-http://127.0.0.1:8080}"
TARGET_URL="${TARGET_URL:-https://accounts.google.com}"
PROFILE_DIR="${CHROME_USER_DATA_DIR:-$HOME/.config/playwright-chromium-profile}"

# Configure display and mutter auth for Cloudtop Xwayland if needed
export DISPLAY="${DISPLAY:-:0}"
if [ -z "$XAUTHORITY" ]; then
  MUTTER_AUTH=$(ls /run/user/$(id -u)/.mutter-Xwaylandauth.* 2>/dev/null | tail -n 1)
  if [ -n "$MUTTER_AUTH" ]; then
    export XAUTHORITY="$MUTTER_AUTH"
  fi
fi

echo "============================================================"
echo " Launching System Chrome with Proxy"
echo " Proxy:       $PROXY_SERVER"
echo " Profile:     $PROFILE_DIR"
echo " Target URL:  $TARGET_URL"
echo " Display:     $DISPLAY"
echo "============================================================"

/usr/bin/google-chrome \
  --proxy-server="$PROXY_SERVER" \
  --ignore-certificate-errors \
  --user-data-dir="$PROFILE_DIR" \
  "$TARGET_URL"
