import sys

import cyclopts

from musictl.adapters.beets import BeetsAdapter
from musictl.adapters.mpd import MpdAdapter
from musictl.config import settings
from musictl.services.playlists import PlaylistService

app = cyclopts.App(name="play", help="Play tracks or playlists")


@app.default
def play(playlist: str | None = None) -> None:
    """Play a named playlist or tracks from stdin.

    If --playlist is given, loads that MPD playlist.
    Otherwise, reads track paths (relative to music dir) from stdin, one per line.

    Usage:
        musictl play --playlist rock
        musictl search 'artist:Beatles' | musictl play
    """
    mpd = MpdAdapter()

    if playlist is not None:
        beets = BeetsAdapter()
        service = PlaylistService(mpd, beets, settings)
        service.load(playlist)
        mpd.play()
        return

    if sys.stdin.isatty():
        print("No playlist specified and no input piped. See --help.", file=sys.stderr)
        sys.exit(1)

    paths = [line.strip() for line in sys.stdin if line.strip()]
    if not paths:
        print("No tracks provided.", file=sys.stderr)
        sys.exit(1)

    mpd.clear()
    for path in paths:
        mpd.add(path)
    mpd.play()
