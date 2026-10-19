# llm-usage

Usage limits and credits for Anthropic (Claude subscription), GitHub Copilot and DeepInfra, in one JSON file and one Alfred keyword.

- `llm-usage` — Python script (stdlib only). Fetches each provider and writes `~/.cache/llm-usage.json`.
- `alfred/` — the "LLM Usage" Alfred workflow. Type `ll` to see a ring chart per limit or credit, plus when it was last updated and whether the last run succeeded.

macOS only. Uses your existing logins: Claude Code's Keychain item, `gh`, and a DeepInfra key from a local script. Run it every 10 minutes with a LaunchAgent; see `AGENTS.md` for the details.
