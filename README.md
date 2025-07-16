# Musictl

A lightweight command‑line tool for managing and playing your music library via **wofi**.

## Features

* Browse folders and start playlists in a few clicks
* Fuzzy search across every track
* Move or delete the currently playing song
* Import new music with automatic renaming and tagging
* Works with any **MPRIS**‑compatible player (DeadBeef, MPD, VLC, etc.)
* Fully configurable through a YAML file

## Quick Start

### Requirements

* **Python ≥ 3.13**
* **wofi** (launcher)
* A music player that supports MPRIS

### Installation

```bash
# Dependencies
pip install pyrofi pyyaml dbus-python mutagen

# Musictl
git clone https://<repo>/musictl
cd musictl
pip install -e .
```

## Configuration

Edit `~/.config/musictl/config.yml` (example):

```yaml
base_path: ~/Dropbox              # Root of your library
ignored_dirs: [downloads, .git, __pycache__]
music_directories: [collection, inbox, dj]
music_extensions: [.mp3, .flac, .wav, .ogg, .m4a]
player_command: deadbeef
track_count_options: [10, 50, 100, ALL]
import_log_file: ~/.config/musictl/import.log
```

## Main Commands

| Command                            | What it does                                                           |
| ---------------------------------- | ---------------------------------------------------------------------- |
| `musictl select`                   | Open wofi, choose a folder, play N random tracks                       |
| `musictl search`                   | Fuzzy‑search for a track and play it                                   |
| `musictl pick <dir>`               | Move current track to `<dir>/<subdir>/YYYY-MM/`                        |
| `musictl delete`                   | Delete current track (with confirmation)                               |
| `musictl import <target> <source>` | Copy files from `<source>` into `<target>/YYYY-MM/` with auto‑renaming |

## Typical Workflow

1. Download an album to `~/Downloads`.
2. Run `musictl import collection/rock ~/Downloads/Album`.
3. Files are renamed to `Artist - Album - 01 - Title.mp3` and logged to `~/.config/musictl/import.log`.
