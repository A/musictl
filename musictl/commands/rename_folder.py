import cyclopts

from musictl.adapters.beets import BeetsAdapter
from musictl.adapters.mpd import MpdAdapter
from musictl.config import settings
from musictl.services.library import LibraryService
from musictl.services.playlists import PlaylistService

app = cyclopts.App(name="rename-folder", help="Rename a folder across all tracks")


@app.default
def rename_folder(old: str, new: str) -> None:
    """Rename a folder: update folder+genre fields on matching tracks, move files, regenerate playlists."""
    beets = BeetsAdapter()
    mpd = MpdAdapter()
    library = LibraryService(beets, settings)
    library.rename_folder(old, new)
    playlists = PlaylistService(mpd, beets, settings)
    playlists.generate_all()
