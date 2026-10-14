#!/bin/bash
# Prepares Claude Code cloud sessions for HyperFrames video work.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

HYPERFRAMES_VERSION="0.8.157"

# Use the preinstalled chrome-headless-shell so renders take the fast
# beginframe capture path instead of downloading a browser.
shopt -s nullglob
shells=(/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell)
shopt -u nullglob
if [ ${#shells[@]} -gt 0 ] && [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export HYPERFRAMES_BROWSER_PATH=\"${shells[-1]}\"" >> "$CLAUDE_ENV_FILE"
fi

# Warm the npm cache with the CLI version the projects under videos/ pin.
npx --yes "hyperframes@${HYPERFRAMES_VERSION}" --version >/dev/null 2>&1 \
  || echo "hyperframes CLI pre-warm failed; it will be fetched on first use" >&2
