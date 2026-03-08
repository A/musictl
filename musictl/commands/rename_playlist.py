import cyclopts

from musictl.adapters.beets import BeetsAdapter
from musictl.adapters.mpd import MpdAdapter
from musictl.config import settings
from musictl.services.playlists import PlaylistService

app = cyclopts.App(name="rename-playlist", help="Rename a playlist across all tracks")


@app.default
def rename_playlist(old: str, new: str) -> None:
    """Rename a playlist: update playlists field on all matching tracks, sync comments, regenerate playlists."""
    mpd = MpdAdapter()
    beets = BeetsAdapter()
    service = PlaylistService(mpd, beets, settings)
    service.rename(old, new)
