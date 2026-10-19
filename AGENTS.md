# llm-usage

One stdlib-only Python script, `llm-usage`, that fetches usage limits and credits
from Anthropic (Claude subscription), GitHub Copilot and DeepInfra, writes
`~/.cache/llm-usage.json`, and prints the same JSON. Meant to be read by
Alfred (`alfred/`, below) / Hammerspoon. Run `./llm-usage` to test; there are no
automated tests.

## Sources

| Provider | Endpoint | Auth |
| --- | --- | --- |
| Anthropic | `api.anthropic.com/api/oauth/usage` (undocumented, used by Claude Code) | Claude Code OAuth token from the Keychain item `Claude Code-credentials` — never refresh it here |
| Copilot | `gh api /copilot_internal/user` (undocumented) | `gh` login |
| DeepInfra | `api.deepinfra.com/payment/checklist` (undocumented); negative `stripe_balance` = credit | Keychain item: service `DEEPINFRA_API_KEY`, account `$USER` |

All three are undocumented and may change; a broken provider shows up as
`"status": "error"` with the message, and the script exits 1.

## Principles

- Minimum that's useful today. Add a provider only when it's actually needed.
- Stdlib only. Every network call / subprocess has a timeout.
- Fail loudly per provider; never drop or fake a value.

## Running

- Scheduled every 10 minutes by the `com.shri.llm-usage` LaunchAgent
  (`~/lawn/launchd/com.shri.llm-usage.plist`, log `~/Library/Logs/llm-usage.log`).

## Alfred workflow (`alfred/`)

"The Alfred workflow" means `alfred/` in this repo: the "LLM Usage" workflow, keyword `ll`.
`llm_usage.py` is its script filter: one row per limit/credit with a ring-chart icon
(cached in `~/.cache/llm-usage-icons/`; delete that folder after changing the drawing),
then a row per failed provider, then an "Updated … ago" row saying whether the last run
fully succeeded (green check), or failed or is stale (red cross). `info.plist` is Alfred's workflow definition.

Alfred loads it through a symlink:
`~/Dropbox/AlfredPrefs/Alfred.alfredpreferences/workflows/user.workflow.323D0302-CE58-459A-9217-4F263F8CF3A9 -> ~/labs/llm-usage/alfred`.
Test with `alfred/llm_usage.py`, which prints Alfred's JSON. If you change the JSON
written by `llm-usage`, update `llm_usage.py` in the same commit.

## Setting it up on another Mac

When asked to set this up, first review `llm-usage` and `alfred/llm_usage.py` for
anything unsafe and report what you found. Then:

1. Check prerequisites; skip a provider (remove it from `PROVIDERS` and `NAMES`)
   rather than fake it if its login is missing:
   - Anthropic: Claude Code logged in with a Claude subscription (Keychain item
     `Claude Code-credentials` exists).
   - Copilot: `gh auth status` succeeds and the account has Copilot.
   - DeepInfra: the user stores their key with
     `security add-generic-password -a "$USER" -s DEEPINFRA_API_KEY -w` (they type it; never ask
     them to paste a key into the chat).
2. Run `./llm-usage` and check every provider reports `"status": "ok"`.
3. Add a LaunchAgent `~/Library/LaunchAgents/<label>.plist` running
   `timeout 90 <repo>/llm-usage > /dev/null` with `StartInterval` 600 and `RunAtLoad`,
   PATH including Homebrew (for `gh`) and wherever `timeout` lives, logging to
   `~/Library/Logs/llm-usage.log` (or change `LOG_FILE` in `alfred/llm_usage.py` to
   match). Load it with `launchctl bootstrap gui/$(id -u) <plist>` and check the log.
4. If they use Alfred: symlink `alfred/` into their Alfred preferences'
   `workflows/` folder as `user.workflow.<new UUID>` (the preferences folder is in
   Alfred → Preferences → Advanced → Syncing, default `~/Library/Application Support/Alfred/Alfred.alfredpreferences`).
   Make sure no other workflow already uses the `ll` keyword.
