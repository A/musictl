import sys
from pathlib import Path

import cyclopts

from musictl.adapters.beets import BeetsAdapter
from musictl.adapters.mpd import MpdAdapter
from musictl.adapters.tagger import TaggerAdapter
from musictl.adapters.yad import YadAdapter
from musictl.config import settings
from musictl.services.library import LibraryService
from musictl.services.playlists import PlaylistService

app = cyclopts.App(name="import", help="Import tracks into beets library")


def _collect_audio_files(paths: tuple[str, ...]) -> list[str]:
    audio_files: list[str] = []
    for p in paths:
        path = Path(p)
        if path.is_file() and path.suffix.lower() in settings.audio_extensions:
            audio_files.append(str(path))
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and child.suffix.lower() in settings.audio_extensions:
                    audio_files.append(str(child))
    return audio_files


@app.default
def import_tracks(*args: str) -> None:
    """Import tracks via beet import. All arguments are passed through."""
    tagger = TaggerAdapter()
    dialog = YadAdapter()

    audio_files = _collect_audio_files(args)

    if audio_files:
        defaults = tagger.read_tags(audio_files[0])
        result = dialog.form(
            "Import Metadata",
            ["Artist", "Album", "Genre"],
            [defaults.get("artist", ""), defaults.get("album", ""), defaults.get("genre", "")],
        )
        if result is None:
            sys.exit(1)
        artist, album, genre = result
        tags: dict[str, str] = {}
        if artist:
            tags["artist"] = artist
        if album:
            tags["album"] = album
        if genre:
            tags["genre"] = genre
        if tags:
            for f in audio_files:
                tagger.write_tags(f, tags)

    beets = BeetsAdapter()
    service = LibraryService(beets, settings)
    service.import_tracks(*args)
    mpd = MpdAdapter()
    mpd.connect()
    mpd.update()
    playlist_service = PlaylistService(mpd, beets, settings)
    playlist_service.regenerate()
