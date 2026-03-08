from musictl.config import Settings
from musictl.protocols import BeetsBackend


class LibraryService:
    def __init__(self, beets: BeetsBackend, settings: Settings) -> None:
        self._beets = beets
        self._settings = settings

    def import_tracks(self, *args: str) -> None:
        self._beets.import_tracks(*args)

    def rename_folder(self, old: str, new: str) -> None:
        """Rename a folder: update folder+genre fields on matching tracks, then move files."""
        tracks = self._beets.query(f"folder:{old}")
        for track in tracks:
            query = f"path:{track['path']}"
            self._beets.modify(query, folder=new, genre=new)
        self._beets.move(f"folder:{new}")
