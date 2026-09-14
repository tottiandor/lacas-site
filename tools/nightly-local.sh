#!/bin/bash
# Collect the news from this Mac and push the result.
#
# Why this exists: The Drum and Creative Review return 403 to GitHub's servers
# (they block datacenter IP ranges), so the nightly GitHub Action can only
# refresh three of the five sources. From an ordinary home or office connection
# all five work. This script does what the Action does, just from here.
#
#   Run it once, by hand:
#       ./tools/nightly-local.sh
#
#   Schedule it to run every morning at 07:00:
#       ./tools/nightly-local.sh --install-schedule
#
#   Stop it running automatically:
#       ./tools/nightly-local.sh --remove-schedule
#
# The Mac has to be awake at that time. macOS runs a missed job shortly after
# it wakes, so an overnight sleep is usually fine. If it never runs, nothing
# breaks - the GitHub Action still refreshes what it can reach, and those two
# sources simply keep the stories they already had.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1

LOG="$REPO/tools/nightly-local.log"
LABEL="com.lacassite.nightly"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

say() {
  printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" | tee -a "$LOG"
}

fail() {
  say "FAILED: $1"
  exit 1
}

# macOS ships python3; a bare `python` often does not exist at all. Check that
# the command actually runs a new enough Python rather than merely existing -
# some systems ship a stub named python3 that only prints an advert.
pick_python() {
  local candidate
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 &&
       "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

PY="$(pick_python)" || fail "no working Python 3.9+ found - install Python first"

# --------------------------------------------------------------- scheduling

install_schedule() {
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$REPO/tools/nightly-local.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>7</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$REPO/tools/nightly-local.log</string>
  <key>StandardErrorPath</key>
  <string>$REPO/tools/nightly-local.log</string>
</dict>
</plist>
PLISTEOF

  # bootstrap is the modern command; load -w still works on older macOS.
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
  if ! launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null; then
    launchctl load -w "$PLIST" 2>/dev/null || fail "could not register the schedule"
  fi
  say "scheduled: will run every day at 07:00"
  say "plist: $PLIST"
}

remove_schedule() {
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || launchctl unload -w "$PLIST" 2>/dev/null
  rm -f "$PLIST"
  say "schedule removed"
}

case "${1:-}" in
  --install-schedule) install_schedule; exit 0 ;;
  --remove-schedule)  remove_schedule;  exit 0 ;;
  "") ;;
  *) echo "usage: $0 [--install-schedule | --remove-schedule]"; exit 2 ;;
esac

# --------------------------------------------------------------- collection

say "--- starting"

# Take any commits the GitHub Action made since last time, so the push below is
# a fast-forward rather than a conflict.
if ! pull_out="$(git pull --rebase --autostash origin main 2>&1)"; then
  fail "git pull: $pull_out"
fi
say "pulled"

if ! collect_out="$("$PY" scrape.py 2>&1)"; then
  say "$collect_out"
  fail "scrape.py did not finish"
fi
while IFS= read -r line; do
  [ -n "$line" ] && say "  $line"
done <<< "$collect_out"

if git diff --quiet -- data/news.json; then
  say "no new stories - nothing to push"
  exit 0
fi

stamp="$(date -u '+%Y-%m-%d %H:%M')"
git add data/news.json || fail "git add"
git commit -q -m "Update news feed from local run ($stamp UTC)" || fail "git commit"
git push -q origin main || fail "git push"

say "pushed - the site rebuilds in a minute or two"
