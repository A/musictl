# Musictl

Music control CLI for MPD + beets. Python 3.13, cyclopts CLI, clean architecture.

## Commands

```bash
just check      # ruff check + basedpyright
just fmt         # ruff fix + ruff format
uv run pytest    # run tests
just sync        # uv sync dependencies
```

## Architecture

Adapters → Services → Commands. All adapter dependencies flow through Protocol interfaces.

- `musictl/adapters/` — thin wrappers: mpd (python-mpd2), beets (beets.library + subprocess), ffmpeg (ffcuesplitter), yad (subprocess)
- `musictl/services/` — business logic, receives adapters via protocol types
- `musictl/commands/` — cyclopts CLI entry points, wired in `__main__.py`
- `musictl/protocols.py` — `MpdBackend`, `BeetsBackend`, `FfmpegBackend`, `DialogBackend`
- `musictl/config.py` — `Settings` dataclass with `music_dir`, `mpd_host`, `mpd_port`, `beets_db_path`, `playlists_dir`
- `stubs/` — type stubs for python-mpd2, ffcuesplitter

## Current State

Steps 1-2 of `docs/implementation-plan.md` are complete (scaffold + adapters + tests). Steps 3-8 (services, commands, completions) are not started.

## Code Style

- Never suppress type errors with `# pyright: ignore` or file-level overrides. Fix the root cause.
- For untyped third-party libraries, create type stubs in `stubs/`. Search PyPI for existing stubs first (`types-{pkg}` or `{pkg}-stubs`).
- Pyright config already disables noisy rules (reportAny, reportUnknownMemberType, etc.) — don't add more suppressions without good reason.
- Ruff handles import sorting and unused imports. Run `just fmt` to auto-fix.

## Beets Domain

- `folder` field — organizes track into directory; also synced to `genre`
- `playlists` field — comma-separated playlist names (custom beets field)
- `comments` field — synced to `playlists:$playlists` for external readers
- Paths: `$folder/$artist - $album - $track - $title` (or `inbox/$genre/...` when no folder)

## Testing

- All adapters tested via mocks in `tests/test_adapters/`
- Services and commands: use mocked adapters (protocol fakes), not real backends
- Pre-commit runs both basedpyright and pytest
