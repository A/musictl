# develop (project extension)

Project-local facts for development.

## Quality-check classification

Hook-enforced (runs automatically at commit, no skill action required):
- ruff (`--fix`)
- ruff-format
- basedpyright (`musictl/`)
- pytest (`tests/ -x -q`)

Configured-but-manual (skill picks the relevant ones per milestone per docs/development_quality_checks.md — not all need to run on every milestone):
- `just check` (lint + typecheck wrapper)
- `just test` (full suite, not the `-x` fast-fail hook variant)
- `just fmt` (auto-fix before commit)

## Dev environment

- `uv`-managed venv — every command runs via `uv run` (`uv sync` to install deps).
- Runtime (not needed for unit tests, which mock backends) requires: a running **MPD** daemon, a **beets** library DB, and config at `~/.config/musictl/config.yml` (keys: `music_dir`, `mpd_host`, `mpd_port`, `beets_db_path`, `playlists_dir`).
- Some commands shell out to external tools: `ffmpeg`/ffcuesplitter (cue-split), `yad` (update/delete dialogs), `beet` CLI (modify/move/import/remove).
- Note: the `beet` subprocess calls use the ambient beets config — integration tests must isolate via `BEETSDIR` to avoid touching the real library.
