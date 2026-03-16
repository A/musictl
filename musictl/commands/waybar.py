import json
import sys

import cyclopts

from musictl.adapters.beets import BeetsAdapter
from musictl.adapters.mpd import MpdAdapter
from musictl.config import settings
from musictl.services.tracks import TrackService

app = cyclopts.App(name="waybar", help="Output current track info for waybar")


def _build_output(service: TrackService) -> str:
    track = service.current_track()
    if track is None:
        return json.dumps({"text": "", "tooltip": "", "class": "stopped"})

    folder = track.get("folder", "")
    playlists = track.get("playlists", "")

    if not folder and not playlists:
        text = "  Inbox"
    else:
        parts = []
        if folder:
            parts.append(f"  {folder} ")
        if playlists:
            parts.append(f"  {playlists}")
        text = " ".join(parts)
    artist = track.get("artist", "")
    title = track.get("title", "")
    if artist and title:
        text += f" 󰯈  {artist} - {title}"
    tooltip = f" {artist} - {title}" if artist and title else ""

    return json.dumps({"text": text, "tooltip": tooltip})


@app.default
def waybar() -> None:
    """Print current track info as JSON for waybar custom module.

    Runs continuously, updating on each player event.
    """
    mpd = MpdAdapter()
    beets = BeetsAdapter()
    service = TrackService(mpd, beets, settings)

    print(_build_output(service), flush=True)

    while True:
        try:
            mpd.idle("player")
        except (OSError, Exception):
            sys.exit(1)
        print(_build_output(service), flush=True)
