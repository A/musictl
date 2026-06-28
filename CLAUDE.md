# Musictl

Music control CLI for MPD + beets. Python 3.13, cyclopts CLI, clean architecture.

## Commands

```bash
just check      # ruff check + basedpyright
just fmt         # ruff fix + ruff format
just test        # run tests
just sync        # uv sync dependencies
```

## Runtime

- Always use `uv run` to execute Python and any venv-dependent commands (e.g. `uv run python`, `uv run pytest`, `uv run musictl`). Never invoke `python` or venv scripts directly.

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

Two tiers, selected by the `e2e` marker:

- `just test` — fast tier (`pytest -m "not e2e"`). Services and commands use protocol fakes; no real backends, daemon, or network.
- `just test-e2e` — Docker e2e tier (`docker compose run --rm test`, marker `e2e`). Runs against a real, pinned beets (2.12.0) + real `beet` CLI inside `Dockerfile.test`. CI runs this on PRs.

E2e seeding has two forms (`tests/support/seeding.py`): `seed_item(...)` inserts DB-only beets `Item` rows (fast, no files) for query/enrichment/collection logic; `make_track(...)` generates tiny tagged silent ffmpeg tracks for the import/move/delete file-op paths.

Isolation invariant (safety-critical): every e2e test binds beets to a `tmp_path` library and points `BEETSDIR` **and** `HOME` at tmp dirs, so no test ever touches the real `~/Music` / `~/.config/beets`. The fixture deliberately sets beets `directory` != `music_dir` to reproduce the 2.12 path-absolutization that the Inbox-enrichment bug needed. `assert_isolated(beets_env, ...)` in `tests/conftest.py` is the shared guard, used by both adapter and service e2e tests.

- All adapters tested in `tests/test_adapters/`; the beets adapter runs against a real seeded Library (no mocks).
- Services and commands: use protocol fakes, not real backends (except the `e2e` enrichment regression, which pairs a fake MPD with a real seeded beets).
- Pre-commit runs ruff, basedpyright, and pytest.
