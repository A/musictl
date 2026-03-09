# Musictl

Music control CLI for **MPD** + **beets**. Manage your library, playlists, and playback from the terminal.

## Prerequisites

- **Python ≥ 3.13**
- **MPD** — running and configured
- **beets** — with library database and custom fields (`folder`, `playlists`, `comments`)
- **YAD** — for interactive dialogs (`update`, `delete-current`)
- **FFmpeg** — for `cue-split`

### Beets Setup

Musictl expects these beets flexible attributes:

- `folder` — organizes tracks into directories (also synced to `genre`)
- `playlists` — comma-separated playlist names
- `comments` — synced to `playlists:$playlists` for external readers

Beets path config should include:

```yaml
paths:
  "folder::.+": $folder/$artist - $album - $track - $title
  default: inbox/$genre/$artist - $album - $track - $title
```

## Installation

```bash
# From PyPI
uv tool install musictl

# Or from source
git clone https://github.com/A/musictl
cd musictl
uv tool install -e .
```

## Commands

| Command | Description |
|---------|-------------|
| `musictl search <query>` | Search beets library, print relative paths |
| `musictl play <playlist>` | Load and play a playlist |
| `musictl play --random [--count N]` | Play N random tracks |
| `musictl update` | Set folder/playlists on current track via YAD dialog, remove from queue |
| `musictl delete-current` | Delete current track from library and disk, remove from queue |
| `musictl clean-current` | Remove current track from MPD queue |
| `musictl import [args]` | Import tracks via `beet import` |
| `musictl cue-split <file> --cue <cue>` | Split audio file by CUE sheet |
| `musictl generate-playlists` | Regenerate all .m3u playlist files |
| `musictl rename-playlist <old> <new>` | Rename a playlist across all tracks |
| `musictl rename-folder <old> <new>` | Rename a folder, move files, update tags |
| `musictl waybar` | JSON output for waybar custom module |

### Piping

```bash
# Search and play results
musictl search 'artist:Beatles' | musictl play

# Search and play from a specific folder
musictl search 'folder:rock' | musictl play
```

### Waybar Integration

Add to your waybar config:

```json
"custom/music": {
    "exec": "musictl waybar",
    "interval": 5,
    "return-type": "json"
}
```

### Hyprland Keybindings

```conf
bind = $mainMod, M, exec, musictl play --random --count 20
bind = $mainMod SHIFT, M, exec, musictl update
bind = $mainMod CTRL, M, exec, musictl delete-current
```

## Development

```bash
just check      # ruff check + basedpyright
just fmt         # ruff fix + ruff format
just test        # run tests
just sync        # uv sync dependencies
```
