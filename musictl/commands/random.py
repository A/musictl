import cyclopts

from musictl.adapters.beets import BeetsAdapter
from musictl.adapters.mpd import MpdAdapter

app = cyclopts.App(name="random", help="Play random tracks")


@app.default
def random(query: str = "", *, count: int = 10) -> None:
    """Pick random tracks from beets and play them.

    Args:
        query: Optional beets query to filter tracks.
        count: Number of random tracks to pick.
    """
    beets = BeetsAdapter()
    paths = beets.random(count, query)
    if not paths:
        return

    mpd = MpdAdapter()
    mpd.clear()
    for path in paths:
        mpd.add(path)
    mpd.play()
