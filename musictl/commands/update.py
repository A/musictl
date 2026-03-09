import logging
import sys

import cyclopts

from musictl.adapters.beets import BeetsAdapter
from musictl.adapters.mpd import MpdAdapter
from musictl.adapters.yad import YadAdapter
from musictl.config import settings
from musictl.services.playlists import PlaylistService
from musictl.services.tracks import TrackService

logger = logging.getLogger(__name__)

app = cyclopts.App(name="update", help="Update current track metadata via dialog")


@app.default
def update() -> None:
    """Show a dialog to update folder and playlists for the currently playing track.

    Sets folder, genre (synced to folder), playlists, and comments fields.
    Moves the file to match the new folder and regenerates playlists.
    """
    mpd = MpdAdapter()
    beets = BeetsAdapter()
    dialog = YadAdapter()
    track_service = TrackService(mpd, beets, settings)

    track = track_service.current_track()
    if track is None:
        print("Nothing playing.", file=sys.stderr)
        sys.exit(1)

    current_folder = track.get("folder", "")
    current_playlists = {p.strip() for p in track.get("playlists", "").split(",") if p.strip()}

    all_folders = beets.all_folders()
    all_playlists = beets.all_playlists()

    # Build YAD form: fields define types, values set initial state
    fields: list[str] = []
    values: list[str] = []

    # Folder: combo-box-entry with existing folders
    folder_options = "!".join(all_folders)
    fields.append("Folder:CBE")
    values.append(f"{current_folder}!{folder_options}")

    # Playlist checkboxes
    for name in sorted(all_playlists):
        fields.append(f"{name}:CHK")
        values.append("TRUE" if name in current_playlists else "FALSE")

    result = dialog.form("Update Track", fields, values)
    if result is None:
        sys.exit(1)

    # Parse form result: first value is folder, rest are checkbox booleans
    new_folder = result[0].strip()
    selected_playlists: list[str] = []
    for i, name in enumerate(sorted(all_playlists)):
        if result[i + 1].upper() == "TRUE":
            selected_playlists.append(name)

    new_playlists = ",".join(selected_playlists)
    logger.info("Updating: folder=%s, playlists=%s", new_folder, new_playlists)
    track_id = track.get("id", "")
    if not track_id:
        print("Cannot determine track ID.", file=sys.stderr)
        sys.exit(1)
    query = f"id:{track_id}"

    # Remove from MPD queue before modify+move, to avoid removing the next track
    track_service.clean_current()

    beets.modify(
        query,
        folder=new_folder,
        genre=new_folder,
        playlists=new_playlists,
        comments=f"playlists:{new_playlists}",
    )

    playlist_service = PlaylistService(mpd, beets, settings)
    playlist_service.regenerate()
