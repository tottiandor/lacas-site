# Collect the news from this machine and push the result.
#
# Why this exists: The Drum and Creative Review return 403 to GitHub's servers
# (they block datacenter IP ranges), so the nightly GitHub Action can only
# refresh three of the five sources. From an ordinary home or office connection
# all five work. This script does what the Action does, just from here.
#
# Run it by hand:
#     powershell -ExecutionPolicy Bypass -File tools\nightly-local.ps1
#
# Or schedule it nightly at 07:00. Run this once, from the project folder:
#     schtasks /create /tn "Lacas Site nightly" /sc daily /st 07:00 /f /tr "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%CD%\tools\nightly-local.ps1\""
#
# Remove it again with:
#     schtasks /delete /tn "Lacas Site nightly" /f
#
# The machine has to be awake at that time. If it is asleep nothing breaks - the
# GitHub Action still refreshes whatever it can reach, and those two sources
# simply keep the stories they already had.

# Deliberately NOT 'Stop': git writes ordinary progress to stderr, which
# PowerShell 5.1 turns into a terminating error under 'Stop'. Exit codes are
# checked explicitly instead.
$ErrorActionPreference = 'Continue'

$repo = Split-Path -Parent $PSScriptRoot   # this script lives in <repo>\tools
Set-Location $repo

$log = Join-Path $repo 'tools\nightly-local.log'

function Say($message) {
    $line = "{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message
    Write-Output $line
    Add-Content -Path $log -Value $line -Encoding utf8
}

function Fail($message) {
    Say "FAILED: $message"
    exit 1
}

Say "--- starting"

# Take any commits the GitHub Action made since last time, so the push below is
# a fast-forward rather than a conflict.
$pull = (git pull --rebase --autostash origin main 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { Fail "git pull: $pull" }
Say "pulled"

$collect = (python scrape.py 2>&1 | Out-String).Trim()
foreach ($line in $collect -split "`r?`n") {
    if ($line.Trim()) { Say "  $line" }
}
if ($LASTEXITCODE -ne 0) { Fail "scrape.py exited $LASTEXITCODE" }

git diff --quiet -- data/news.json
if ($LASTEXITCODE -eq 0) {
    Say "no new stories - nothing to push"
    exit 0
}

$stamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm')
git add data/news.json
if ($LASTEXITCODE -ne 0) { Fail "git add" }

$commit = (git commit -q -m "Update news feed from local run ($stamp UTC)" 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { Fail "git commit: $commit" }

$push = (git push -q origin main 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { Fail "git push: $push" }

Say "pushed - the site rebuilds in a minute or two"
