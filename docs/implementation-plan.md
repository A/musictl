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
│   ├── play.py
│   ├── random.py
│   ├── update.py
│   ├── delete_current.py
│   ├── clean_current.py
│   ├── import_tracks.py
│   ├── cue_split.py
│   ├── generate_playlists.py
│   ├── rename_playlist.py
│   └── rename_folder.py
├── protocols.py         # Protocol interfaces for adapters
└── config.py            # Settings (music dir, mpd host/port, etc.)
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
- [x] Create `musictl/config.py` with settings (music_dir, mpd_host, mpd_port, beets_db_path)
- [x] Create `musictl/protocols.py` with adapter interfaces
- [x] Verify `just check` passes on empty project

### Step 2: Adapters — MPD, Beets, Ffmpeg, YAD
- [ ] Implement `MpdAdapter` wrapping `python-mpd2`:
  - `connect()`, `current_song()`, `add(uri)`, `play()`, `clear()`, `delete(pos)`, `load_playlist(name)`, `list_playlists()`, `search(query)`, `update()`, `current_position()`, `queue_count()`
  - Auto-reconnect on connection loss
- [ ] Implement `BeetsAdapter`:
  - Query/modify via `beets.library.Library` (open `~/.config/beets/library.db`)
  - `query(q)` → list of item dicts (path, artist, title, folder, playlists, id)
  - `get_field(q, field)`, `modify(q, **fields)`, `all_folders()`, `all_playlists()`
  - `move(q)`, `remove(q, delete)`, `import_tracks(*args)`, `random(n, q)` via subprocess (`beet move`, `beet remove`, `beet import`, `beet random`)
  - `sync_comments(q)` — sync playlists field to comments
- [ ] Implement `FfmpegAdapter` wrapping `ffcuesplitter`:
  - `split_cue(audio_file, cue_file, output_dir)` → list of output file paths
- [ ] Implement `YadAdapter`:
  - `confirm(title, text)` → bool
  - `form(title, fields)` → list[str] | None (supports CBE, CHK, LBL, entry)
  - `notify(title, text)` → via `notify-send`
- [ ] Unit tests with mocked backends

### Step 3: Service Layer
- [ ] `TrackService(mpd: MpdBackend, beets: BeetsBackend)`:
  - `current_track()` → returns current track info from MPD + beets enrichment
  - `search(query: str)` → beets query results
  - `delete_current(confirm: bool)` → yad confirm, beet remove -d, mpd queue update
  - `clean_current()` → remove current track from MPD queue (`mpd.delete(pos)`)
- [ ] `PlaylistService(mpd: MpdBackend, beets: BeetsBackend)`:
  - `load(name: str)` → `mpd.clear()` + `mpd.load_playlist(name)`
  - `generate_all()` → generates all playlist types:
    - inbox.m3u — tracks without `folder`
    - playlist_*.m3u — by `playlists` field (each comma-separated value)
    - {folder}.m3u — by `folder` field
    - no_playlist.m3u — tracks with folder but no playlists
  - `rename(old_name, new_name)` → update `playlists` field on all matching tracks, sync comments, regenerate
- [ ] `LibraryService(beets: BeetsBackend)`:
  - `import_tracks(*args)` → delegate to `beet import`
  - `rename_folder(old, new)` → update `folder` field on matching tracks, `beet move`
- [ ] `CueSplitService(ffmpeg: FfmpegBackend)`:
  - `split(file, cue)` → split audio file by CUE sheet, return output paths
- [ ] Unit tests with mocked adapters

### Step 4: Commands — play, search, random
- [ ] `musictl search <query>` — `beets.query(query)` → print results, add to MPD, play
- [ ] `musictl play playlist <playlist>` — `mpd.clear()`, `mpd.load_playlist()`, `mpd.play()`
- [ ] `musictl random <playlist> [--count N]` — load playlist tracks, pick N random, add to MPD, play
- [ ] Wire commands in `__main__.py` via cyclopts

### Step 5: Commands — update, delete-current, clean-current
- [ ] `musictl update` — get current track from MPD, lookup in beets, show yad form (folder CBE + playlist checkboxes), apply modifications, `beet move`, sync comments, regenerate playlists, remove from MPD queue
- [ ] `musictl delete-current` — yad confirm, `beet remove -d`, remove from MPD queue, mpd update
- [ ] `musictl clean-current` — simply remove current track position from MPD queue (designed to be chained: `musictl update && musictl clean-current`)

### Step 6: Commands — import, cue-split, generate-playlists
- [ ] `musictl import .` — wrapper around `beet import`
- [ ] `musictl cue-split <file> -c <cue>` — uses `CueSplitService` → `FfmpegAdapter` to split audio
- [ ] `musictl generate-playlists` — call `PlaylistService.generate_all()`, write .m3u files to `~/Music/playlists/`

### Step 7: Commands — rename-playlist, rename-folder
- [ ] `musictl rename-playlist <old> <new>` — update playlists field across all matching tracks, sync comments, regenerate playlists
- [ ] `musictl rename-folder <old> <new>` — update folder+genre fields, `beet move`, regenerate playlists

### Step 8: Shell Completions & README
- [ ] Configure cyclopts shell completion generation
- [ ] Dynamic completions for playlist names, folder names (from beets)
- [ ] Update README.md:
  - New feature list and command reference
  - Prerequisites: MPD setup, beets setup (config, plugins, custom fields)
  - Installation via uv
  - Hyprland keybinding examples
