import sys

import cyclopts

from musictl.adapters.beets import BeetsAdapter
from musictl.adapters.mpd import MpdAdapter
from musictl.config import settings
from musictl.services.tracks import TrackService

app = cyclopts.App(name="clean-current", help="Remove current track from MPD queue")


@app.default
def clean_current() -> None:
    """Remove the currently playing track from the MPD queue."""
    mpd = MpdAdapter()
    beets = BeetsAdapter()
    service = TrackService(mpd, beets, settings)
    if not service.clean_current():
        print("Nothing playing.", file=sys.stderr)
        sys.exit(1)
