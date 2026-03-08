import sys

import cyclopts

from musictl.adapters.beets import BeetsAdapter
from musictl.adapters.mpd import MpdAdapter
from musictl.adapters.yad import YadAdapter
from musictl.config import settings
from musictl.services.tracks import TrackService

app = cyclopts.App(name="delete-current", help="Delete current track from library and disk")


@app.default
def delete_current() -> None:
    """Delete the currently playing track from beets library, disk, and MPD queue."""
    mpd = MpdAdapter()
    beets = BeetsAdapter()
    dialog = YadAdapter()
    service = TrackService(mpd, beets, settings)
    if not service.delete_current(dialog):
        print("Nothing playing or cancelled.", file=sys.stderr)
        sys.exit(1)
