## Musictl Restart

In the scope of this project we're just rewriting musictl from scratch.
Current project files are redundant, and can be removed fully.
Readme should be updated, and also collect details on setup beets and mpd



## technical stack

- uv for package management
- justfile
- basedpyright

## Features

- musictl cue-split <file> -c <cue>
- musictl import . # beets import
- musictl search <beets query>
- musictl play playlist <playlist> # loads playlist to mpd
- musictl update - shows update modal via `yad`
- musictl clean-current - cleans current track in mpd queue, can be combined via update through && to decouple current logic in ~/.config/hypr/config.d/20-key-bindings.conf
- musictl generate-playlists - generate playlists, actually, next types of playlists should be generated:
    - inbox - trachs without $folder
    - by $playlists field in beats, which can contain multiple playlists
    - by $folder
- musictl random <playlist> [--count int] - plays random `count` tracks from the playlist
- musictl delete-current # deletes current track via `yad` confirmation
- musictl rename-playlist <old_name> <new_name> - renames playlist across all library
- muscitl rename-folder <old_name> <new_name>, updates files with beet move.
- Autocompletion


## Architecture

- mpd should be wrapped into an adapter encapsulates interaction with MDP
- beets should be also wrapped
- business logic should be in service layer (playlist service, tracks service with query(), etc that uses beets adapter under the hood), services should relay on backend interfaces (mdp, beets, etc)
- command should orchestrate services.

## Extra Resources

Check ./docs/overview.md and ./docs/best-practices.md for details, this file is the main
source of truth.

## Out of Scope:

- AI tagging

## Next Steps

Prepare detailed plan on the implementation. Check best python libraries for this problem.
Split into steps and then show plan to user to confirm. Steps should be todos to implement
one by one in separate sessions, and mark them as implemented.

Show plan to user, then write it into docs/implementation-plan.md



