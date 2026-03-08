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
- `musictl/log.py` — logging setup, controlled by `-v` flags
- `stubs/` — type stubs for python-mpd2, ffcuesplitter

## CLI Commands

- `search <query>` — search beets, print relative paths
- `play [--playlist NAME] [--random] [--count N]` — play playlist, random tracks, or stdin paths
- `update` — YAD dialog to set folder/playlists on current track, modify+move via `beet modify -m`, regenerate playlists
- `delete-current` — confirm via YAD, delete from beets+disk, regenerate playlists
- `clean-current` — remove current track from MPD queue
- `import [args]` — wrapper around `beet import`
- `cue-split <file> --cue <cue>` — split audio by CUE sheet
- `generate-playlists` — full regeneration of all .m3u files
- `rename-playlist <old> <new>` — rename playlist across all tracks
- `rename-folder <old> <new>` — rename folder+genre, move files
- `waybar` — JSON output (text/tooltip) for waybar custom module

## Playlist Generation

`PlaylistService._build_playlists()` builds the full set, used by both `generate_all()` (overwrite) and `regenerate()` (diff-based).

Generated playlists (all lowercase_snake_case .m3u):
- `inbox` — tracks without a folder
- `{folder}` — all tracks in that folder
- `playlist_{name}` — tracks tagged with that playlist
- `no_playlist` — tracks with folder but no playlist tags
- `collection` — all non-inbox tracks
- `all` — everything

## Beets Integration

- `modify()` uses `beet modify -y -m` (subprocess) — handles both fixed and flexible attributes, moves files in one step
- `query()`, `get_field()`, `all_folders()`, `all_playlists()` use `beets.library.Library` (Python API)
- `move()`, `remove()`, `import_tracks()`, `random()` use subprocess

## Beets Domain

- `folder` field — organizes track into directory; also synced to `genre`
- `playlists` field — comma-separated playlist names (custom beets flexible attribute)
- `comments` field — synced to `playlists:$playlists` for external readers
- Paths: `$folder/$artist - $album - $track - $title` (or `inbox/$genre/...` when no folder)

## Code Style

- Never suppress type errors with `# pyright: ignore` or file-level overrides. Fix the root cause.
- For untyped third-party libraries, create type stubs in `stubs/`. Search PyPI for existing stubs first (`types-{pkg}` or `{pkg}-stubs`).
- Pyright config already disables noisy rules (reportAny, reportUnknownMemberType, etc.) — don't add more suppressions without good reason.
- Ruff handles import sorting and unused imports. Run `just fmt` to auto-fix.

## Testing

- All adapters tested via mocks in `tests/test_adapters/`
- Services and commands: use mocked adapters (protocol fakes), not real backends
- Pre-commit runs ruff, basedpyright, and pytest
