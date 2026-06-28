"""Seeding helpers for the e2e beets harness.

Two tiers:

- `seed_item` — DB-only: inserts a beets `Item` row with a chosen path form,
  no file on disk. Fast and deterministic, for query/enrichment/collection
  logic.
- `make_track` — generates a tiny tagged silent audio file via ffmpeg, for the
  import/move/delete file-op paths that need real files.

On-read path form per beets version
-----------------------------------
`seed_item` stores `path` as bytes exactly as given. How beets reports it back
on read is version-sensitive:

- **beets 2.7** returns the stored bytes unchanged. A music_dir-relative path
  like `b"Ambient/x.flac"` reads back relative.
- **beets 2.12** absolutizes a relative stored path against the library
  `directory` from the config, e.g. `directory/Ambient/x.flac`.

The discriminating Inbox-bug condition (the reported path NOT equalling the
MPD-constructed absolute path) is produced by the fixture's `directory` !=
`music_dir` split, not by anything in this module. Seed with a music_dir-
relative path to exercise it.
"""

import functools
import shutil
import subprocess
import tempfile
from pathlib import Path

from beets.library import Item, Library
from mutagen.flac import FLAC


def seed_item(
    lib: Library,
    *,
    path: str,
    folder: str = "",
    playlists: str = "",
    artist: str = "Artist",
    title: str = "Title",
    album: str = "Album",
) -> Item:
    item = Item(
        path=path.encode(),
        artist=artist,
        title=title,
        album=album,
    )
    item.folder = folder
    item.playlists = playlists
    lib.add(item)
    return item


@functools.cache
def _silent_base() -> Path:
    """Generate the base 1s silent FLAC once per process (session cache)."""
    base = Path(tempfile.mkdtemp(prefix="musictl-silent-")) / "silence.flac"
    subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1", "-y", str(base)],
        check=True,
        capture_output=True,
    )
    return base


def make_track(directory: Path, rel_path: str, **tags: str) -> Path:
    """Copy the cached silent base to `directory/rel_path` and tag it."""
    dest = Path(directory) / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(_silent_base(), dest)
    if tags:
        audio = FLAC(dest)
        for key, value in tags.items():
            audio[key] = [value]
        audio.save()
    return dest
