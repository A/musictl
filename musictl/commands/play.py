import random as random_mod
import sys

import cyclopts

from musictl.adapters.beets import BeetsAdapter
from musictl.adapters.mpd import MpdAdapter
from musictl.config import settings
from musictl.services.playlists import PlaylistService

app = cyclopts.App(name="play", help="Play tracks or playlists")


@app.default
def play(
    playlist: str | None = None,
    *,
    random: bool = False,
    count: int = 10,
) -> None:
    """Play a named playlist or tracks from stdin.

    Usage:
        musictl play rock
        musictl play rock --random --count 5
        musictl play --random --count 20
        musictl search 'artist:Beatles' | musictl play
    """
    mpd = MpdAdapter()

    if random:
        if playlist is not None:
            tracks = mpd.list_playlist_tracks(playlist)
        else:
            beets = BeetsAdapter()
            tracks = [t.get("path", "") for t in beets.query("") if t.get("path")]
        if not tracks:
            print("No tracks found.", file=sys.stderr)
            sys.exit(1)
        selected = random_mod.sample(tracks, min(count, len(tracks)))
        mpd.clear()
        for path in selected:
            mpd.add(path)
        mpd.play()
        return

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
