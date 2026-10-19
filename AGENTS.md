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
fully succeeded. `info.plist` is Alfred's workflow definition.

Alfred loads it through a symlink:
`~/Dropbox/AlfredPrefs/Alfred.alfredpreferences/workflows/user.workflow.323D0302-CE58-459A-9217-4F263F8CF3A9 -> ~/labs/llm-usage/alfred`.
Test with `alfred/llm_usage.py`, which prints Alfred's JSON. If you change the JSON
written by `llm-usage`, update `llm_usage.py` in the same commit.
