# Musictl — Feature Overview

## Commands

| # | Command | `music` (bash) | `musictl` (python) | Notes |
|---|---------|:-:|:-:|-------|
| 1 | **play / select** | `play [inbox\|collection] [filters...]` | `select` — wofi browse by directory, pick track count | bash uses beets queries; musictl browses folder tree |
| 2 | **search** | `search` — wofi over MPD | `search` — wofi over file tree | bash searches MPD; musictl searches filesystem |
| 3 | **playlist** | `playlist` — load MPD playlist via wofi | — | musictl has no equivalent |
| 4 | **random** | `random` — pick count via wofi, beet random | (part of `select` — pick N random tracks) | |
| 5 | **update** | `update` — yad GUI: edit folder + playlists on current track | — | no musictl equivalent |
| 6 | **collect** | `collect` — triage inbox track: assign folder + playlists | — | no musictl equivalent |
| 7 | **pick** | — | `pick <dir>` — move current MPRIS track to subdir/YYYY-MM/ | no bash equivalent |
| 8 | **inbox** | `inbox` — queue all uncollected tracks | — | musictl can filter via `select` |
| 9 | **import** | `import` — thin `beet import` wrapper | `import <target> <source>` — auto-tag, rename, organize, CUE split | musictl is much richer |
| 10 | **delete** | `delete` — yad confirm, beet remove -d | `delete` — wofi confirm, file delete via MPRIS | bash deletes from beets; musictl deletes file directly |
| 11 | **splupdate** | `splupdate` — regenerate all .m3u files | — | no musictl equivalent |
| 12 | **rename_playlist** | `rename_playlist` — rename across all tracks | — | no musictl equivalent |
| 13 | **ai-analyze** | — | `ai-analyze [--dry-run] [--force]` — GPT-4o genre tagging | unique to musictl |

## User Stories

1. **Triage new music (inbox workflow):** Import new tracks, play them, and for each track decide to collect (assign folder/playlist) or delete.
   - bash: `import` → `inbox` → `collect` / `delete`
   - musictl: `import` → `select` → `pick` / `delete`

2. **Browse & play by genre/folder:** Play entire collection or a subset.
   - bash: `play collection`, `play genre:Rock`
   - musictl: `select` → browse directory tree → pick track count

3. **Quick search & play:** Fuzzy-search library and play a specific track.
   - bash: `search` (MPD-based)
   - musictl: `search` (filesystem-based)

4. **Playlist management:** Load, assign, rename, and regenerate playlists.
   - bash: `playlist`, `splupdate`, `rename_playlist`, playlist assignment in `collect`/`update`
   - musictl: **not supported**

5. **Edit track metadata:** Reassign folder/playlists on the currently playing track.
   - bash: `update` (yad GUI)
   - musictl: **not supported**

6. **Discovery / shuffle:** Queue random tracks.
   - bash: `random`
   - musictl: part of `select` (pick N random tracks from a folder)

7. **Library cleanup:** Delete unwanted tracks.
   - bash: `delete` (beets remove + disk)
   - musictl: `delete` (direct file delete)

8. **Smart import with organization:** Import with auto-tagging, renaming, and CUE splitting.
   - bash: thin `beet import` wrapper
   - musictl: full pipeline — metadata extraction, filename sanitization, `Artist - Album - ## - Title` renaming, `YYYY-MM/` organization, CUE sheet splitting, import logging

9. **Organize while listening:** Move the currently playing track to a category folder.
   - bash: **not supported** (closest is `collect`/`update` which use beets folder field)
   - musictl: `pick <dir>` → select subfolder → moves to `subdir/YYYY-MM/`

10. **AI-powered genre tagging:** Automatically analyze and tag tracks with genres using web research.
    - bash: **not supported**
    - musictl: `ai-analyze` — GPT-4o + DuckDuckGo, configurable genre list, dry-run mode, bilingual (EN/RU)
