import cyclopts

from musictl.adapters.beets import BeetsAdapter
from musictl.adapters.mpd import MpdAdapter
from musictl.config import settings
from musictl.services.playlists import PlaylistService

app = cyclopts.App(name="generate-playlists", help="Generate all playlist .m3u files")


@app.default
def generate_playlists() -> None:
    """Generate all playlist .m3u files from beets library data."""
    mpd = MpdAdapter()
    beets = BeetsAdapter()
    service = PlaylistService(mpd, beets, settings)
    written = service.generate_all()
    for path in written:
        print(path)
