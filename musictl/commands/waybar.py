import json
import sys

import cyclopts

from musictl.adapters.beets import BeetsAdapter
from musictl.adapters.mpd import MpdAdapter
from musictl.config import settings
from musictl.services.tracks import TrackService

app = cyclopts.App(name="waybar", help="Output current track info for waybar")


@app.default
def waybar() -> None:
    """Print current track folder and playlists as JSON for waybar custom module."""
    mpd = MpdAdapter()
    beets = BeetsAdapter()
    service = TrackService(mpd, beets, settings)

    track = service.current_track()
    if track is None:
        print(json.dumps({"text": "", "tooltip": "", "class": "stopped"}))
        sys.exit(0)

    folder = track.get("folder", "")
    playlists = track.get("playlists", "")

    parts = []
    if folder:
        parts.append(f"F:{folder}")
    if playlists:
        parts.append(f"P:{playlists}")

    text = " ".join(parts)
    artist = track.get("artist", "")
    title = track.get("title", "")
    tooltip = f"{artist} - {title}" if artist and title else ""

    print(json.dumps({"text": text, "tooltip": tooltip}))
