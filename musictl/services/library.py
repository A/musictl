import logging

from musictl.config import Settings
from musictl.protocols import BeetsBackend

logger = logging.getLogger(__name__)


class LibraryService:
    def __init__(self, beets: BeetsBackend, settings: Settings) -> None:
        self._beets = beets
        self._settings = settings

    def import_tracks(self, *args: str) -> None:
        logger.info("Importing tracks: %s", args)
        self._beets.import_tracks(*args)

    def rename_folder(self, old: str, new: str) -> None:
        """Rename a folder: update folder+genre fields on matching tracks, then move files."""
        logger.info("Renaming folder: %s -> %s", old, new)
        tracks = self._beets.query(f"folder:{old}")
        logger.info("Found %d tracks to update", len(tracks))
        for track in tracks:
            query = f"id:{track['id']}"
            self._beets.modify(query, folder=new, genre=new)
        self._beets.move(f"folder:{new}")
