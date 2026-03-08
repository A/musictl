import logging
from pathlib import Path

from musictl.config import Settings
from musictl.protocols import BeetsBackend, DialogBackend, MpdBackend

logger = logging.getLogger(__name__)


class TrackService:
    def __init__(self, mpd: MpdBackend, beets: BeetsBackend, settings: Settings) -> None:
        self._mpd = mpd
        self._beets = beets
        self._music_dir = settings.music_dir

    def current_track(self) -> dict[str, str] | None:
        song = self._mpd.current_song()
        if song is None:
            logger.info("No track currently playing")
            return None
        file = song.get("file", "")
        if not file:
            return song
        # Enrich with beets metadata using the file path
        full_path = str(self._music_dir / file)
        items = self._beets.query(f"path:{full_path}")
        if items:
            song.update(items[0])
            logger.info("Current track: %s - %s", song.get("artist"), song.get("title"))
        else:
            logger.debug("No beets metadata for %s", file)
        return song

    def search(self, query: str) -> list[dict[str, str]]:
        return self._beets.query(query)

    def delete_current(self, dialog: DialogBackend) -> bool:
        track = self.current_track()
        if track is None:
            return False
        title = track.get("title", "Unknown")
        artist = track.get("artist", "Unknown")
        if not dialog.confirm("Delete track", f"Delete '{artist} - {title}'?"):
            logger.info("Delete cancelled by user")
            return False
        # Remove from beets (and delete file)
        track_id = track.get("id", "")
        if track_id:
            logger.info("Deleting track id=%s: %s", track_id, track.get("path", ""))
            self._beets.remove(f"id:{track_id}", delete=True)
        self._mpd.update()
        return True

    def clean_current(self) -> bool:
        pos = self._mpd.current_position()
        if pos is None:
            return False
        self._mpd.delete(pos)
        return True

    def relative_path(self, absolute_path: str) -> str:
        """Convert an absolute path to a path relative to music_dir."""
        try:
            return str(Path(absolute_path).relative_to(self._music_dir))
        except ValueError:
            return absolute_path
