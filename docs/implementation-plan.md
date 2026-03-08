# Implementation Plan

## Libraries

| Area | Package | Notes |
|------|---------|-------|
| CLI framework | `cyclopts` | Type-hint-driven, built-in shell completions (bash/zsh/fish) |
| MPD client | `python-mpd2` | Only maintained Python MPD client, sync + async |
| Beets | `beets` | Use `beets.library.Library` for queries/modifications; `subprocess` for `beet import` and `beet move` |
| CUE splitting | `ffcuesplitter` | FFmpeg-based, handles parsing + splitting + tagging |
| YAD dialogs | subprocess | Thin custom wrapper (~30 LOC), no good PyPI package exists |

## Beets Schema (from existing config)

- `folder` — organizes track into directory (`paths: "folder::.+": $folder/...`)
- `playlists` — comma-separated playlist names (custom field)
- `comments` — synced to `playlists:$playlists` for external readers
- `genre` — set equal to `folder` on collect/update
- Path when folder set: `$folder/$artist - $album - $track - $title`
- Path when no folder: `inbox/$genre/$artist - $album - $track - $title`

## Project Structure

```
musictl/
├── __init__.py
├── __main__.py          # cyclopts app, command registration
├── adapters/
│   ├── __init__.py
│   ├── mpd.py           # MpdAdapter (python-mpd2)
│   ├── beets.py         # BeetsAdapter (beets.library + subprocess)
│   ├── ffmpeg.py        # FfmpegAdapter (ffcuesplitter)
│   └── yad.py           # YadAdapter (subprocess wrapper)
├── services/
│   ├── __init__.py
│   ├── tracks.py        # TrackService (search, delete, current track)
│   ├── playlists.py     # PlaylistService (generate, rename, load)
│   ├── library.py       # LibraryService (import, rename-folder)
│   └── cue_split.py     # CueSplitService (split audio by CUE sheet)
├── commands/
│   ├── __init__.py
│   ├── search.py
│   ├── play.py           # play + random (merged)
│   ├── update.py
│   ├── delete_current.py
│   ├── clean_current.py
│   ├── import_tracks.py
│   ├── cue_split.py
│   ├── generate_playlists.py
│   ├── rename_playlist.py
│   ├── rename_folder.py
│   └── waybar.py
├── protocols.py         # Protocol interfaces for adapters
├── config.py            # Settings (music dir, mpd host/port, etc.)
└── log.py               # Logging setup (-v/-vv/-vvv)
pyproject.toml
Justfile
.pre-commit-config.yaml
README.md
tests/
├── __init__.py
├── conftest.py
├── test_adapters/
├── test_services/
└── test_commands/
```

## Adapter Interfaces (protocols.py)

```python
from typing import Protocol

class MpdBackend(Protocol):
    def connect(self) -> None: ...
    def current_song(self) -> dict[str, str] | None: ...
    def add(self, uri: str) -> None: ...
    def play(self, pos: int = 0) -> None: ...
    def clear(self) -> None: ...
    def delete(self, pos: int) -> None: ...
    def load_playlist(self, name: str) -> None: ...
    def list_playlists(self) -> list[str]: ...
    def search(self, query: str) -> list[dict[str, str]]: ...
    def update(self) -> None: ...
    def current_position(self) -> int | None: ...
    def queue_count(self) -> int: ...

class BeetsBackend(Protocol):
    def query(self, query: str) -> list[dict[str, str]]: ...
    def get_field(self, query: str, field: str) -> str: ...
    def modify(self, query: str, **fields: str) -> None: ...
    def move(self, query: str) -> None: ...
    def remove(self, query: str, delete: bool = False) -> None: ...
    def import_tracks(self, *args: str) -> None: ...
    def all_folders(self) -> list[str]: ...
    def all_playlists(self) -> list[str]: ...
    def random(self, count: int, query: str = "") -> list[str]: ...

class FfmpegBackend(Protocol):
    def split_cue(self, audio_file: str, cue_file: str, output_dir: str) -> list[str]: ...

class DialogBackend(Protocol):
    def confirm(self, title: str, text: str) -> bool: ...
    def form(self, title: str, fields: list) -> list[str] | None: ...
    def notify(self, title: str, text: str) -> None: ...
```

---

## Steps

### Step 1: Project Scaffold
- [x] Remove old source files (`musictl/*.py` except `__init__.py`)
- [x] Remove `dist/` directory
- [x] Rewrite `pyproject.toml`: swap to hatchling build backend, add new deps (`cyclopts`, `python-mpd2`, `beets`, `ffcuesplitter`), add ruff + basedpyright config
- [x] Create `Justfile` with recipes: `check`, `lint`, `fmt`, `typecheck`, `sync`, `test`
- [x] Create `.pre-commit-config.yaml` (ruff, basedpyright)
- [x] Create directory structure: `musictl/adapters/`, `musictl/services/`, `musictl/commands/`, `tests/`
- [x] Create `musictl/__main__.py` with empty cyclopts app
- [x] Create `musictl/config.py` with settings (music_dir, mpd_host, mpd_port, beets_db_path, playlists_dir)
- [x] Create `musictl/protocols.py` with adapter interfaces
- [x] Verify `just check` passes on empty project

### Step 2: Adapters — MPD, Beets, Ffmpeg, YAD
- [x] Implement `MpdAdapter` wrapping `python-mpd2`:
  - `connect()`, `current_song()`, `add(uri)`, `play()`, `clear()`, `delete(pos)`, `load_playlist(name)`, `list_playlists()`, `search(query)`, `update()`, `current_position()`, `queue_count()`
  - Auto-reconnect on connection loss
- [x] Implement `BeetsAdapter`:
  - Query via `beets.library.Library` (open `~/.config/beets/library.db`)
  - `query(q)` → list of item dicts (path, artist, title, folder, playlists, id)
  - `get_field(q, field)`, `all_folders()`, `all_playlists()`
  - `modify(q, **fields)` via `beet modify -y -m` (subprocess — handles flexible attributes + moves files)
  - `move(q)`, `remove(q, delete)`, `import_tracks(*args)`, `random(n, q)` via subprocess (`beet move`, `beet remove`, `beet import`, `beet random`)
- [x] Implement `FfmpegAdapter` wrapping `ffcuesplitter`:
  - `split_cue(audio_file, cue_file, output_dir)` → list of output file paths
- [x] Implement `YadAdapter`:
  - `confirm(title, text)` → bool
  - `form(title, fields)` → list[str] | None (supports CBE, CHK, LBL, entry)
  - `notify(title, text)` → via `notify-send`
- [x] Unit tests with mocked backends
- [x] Type stubs for untyped libraries (mpd, ffcuesplitter) in `stubs/`

### Step 3: Service Layer
- [x] `TrackService(mpd: MpdBackend, beets: BeetsBackend, settings: Settings)`:
  - `current_track()` → returns current track info from MPD + beets enrichment
  - `search(query: str)` → beets query results
  - `delete_current(dialog: DialogBackend)` → yad confirm, beet remove -d, mpd queue update
  - `clean_current()` → remove current track from MPD queue (`mpd.delete(pos)`)
  - `relative_path(absolute_path)` → convert absolute path to music_dir-relative
- [x] `PlaylistService(mpd: MpdBackend, beets: BeetsBackend, settings: Settings)`:
  - `load(name: str)` → `mpd.clear()` + `mpd.load_playlist(name)`
  - `_build_playlists()` → shared logic that builds full set of playlist name → paths
  - `generate_all()` → overwrites all .m3u files (lowercase_snake_case names):
    - inbox.m3u — tracks without `folder`
    - {folder}.m3u — by `folder` field
    - playlist_{name}.m3u — by `playlists` field (each comma-separated value)
    - no_playlist.m3u — tracks with folder but no playlists
    - collection.m3u — all non-inbox tracks
    - all.m3u — all tracks
  - `regenerate()` → diff-based: only writes changed files, removes stale ones
  - `rename(old_name, new_name)` → update `playlists` field on all matching tracks, sync comments, regenerate
- [x] `LibraryService(beets: BeetsBackend, settings: Settings)`:
  - `import_tracks(*args)` → delegate to `beet import`
  - `rename_folder(old, new)` → update `folder` field on matching tracks, `beet move`
- [x] `CueSplitService(ffmpeg: FfmpegBackend)`:
  - `split(file, cue)` → split audio file by CUE sheet, return output paths
- [x] Unit tests with mocked adapters

### Step 4: Commands — play, search, random
- [x] `musictl search <query>` — `beets.query(query)` → print relative paths, one per line
- [x] `musictl play [--playlist <name>] [--random] [--count N] [--query Q]` — load MPD playlist, play random tracks, or read track paths from stdin
- [x] Wire commands in `__main__.py` via cyclopts

### Step 5: Commands — update, delete-current, clean-current
- [x] `musictl update` — get current track from MPD, lookup in beets, show yad form (folder CBE + playlist checkboxes), apply modifications via `beet modify -m` (modify+move in one step), sync comments, regenerate playlists, remove from MPD queue
- [x] `musictl delete-current` — yad confirm, `beet remove -d`, remove from MPD queue, regenerate playlists
- [x] `musictl clean-current` — simply remove current track position from MPD queue (designed to be chained: `musictl update && musictl clean-current`)

### Step 6: Commands — import, cue-split, generate-playlists
- [x] `musictl import .` — wrapper around `beet import`
- [x] `musictl cue-split <file> -c <cue>` — uses `CueSplitService` → `FfmpegAdapter` to split audio
- [x] `musictl generate-playlists` — call `PlaylistService.generate_all()`, write .m3u files to `~/Music/playlists/`

### Step 7: Commands — rename-playlist, rename-folder, waybar
- [x] `musictl rename-playlist <old> <new>` — update playlists field across all matching tracks, sync comments, regenerate playlists
- [x] `musictl rename-folder <old> <new>` — update folder+genre fields, `beet modify -m`, regenerate playlists
- [x] `musictl waybar` — output current track folder/playlists as JSON for waybar custom module

### Step 8: Shell Completions & README
- [ ] Configure cyclopts shell completion generation
- [ ] Dynamic completions for playlist names, folder names (from beets)
- [ ] Update README.md:
  - New feature list and command reference
  - Prerequisites: MPD setup, beets setup (config, plugins, custom fields)
  - Installation via uv
  - Hyprland keybinding examples
