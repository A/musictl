from musictl.config import Settings
from musictl.services.library import LibraryService


class FakeBeets:
    def __init__(self) -> None:
        self._items: list[dict[str, str]] = []
        self.modifications: list[tuple[str, dict[str, str]]] = []
        self.imported: list[tuple[str, ...]] = []
        self.moved: list[str] = []

    def query(self, query: str) -> list[dict[str, str]]:
        if query.startswith("folder:"):
            folder = query[7:]
            return [i for i in self._items if i.get("folder") == folder]
        return self._items

    def get_field(self, query: str, field: str) -> str:
        return ""

    def modify(self, query: str, **fields: str) -> None:
        self.modifications.append((query, fields))

    def move(self, query: str) -> None:
        self.moved.append(query)

    def remove(self, query: str, delete: bool = False) -> None: ...

    def import_tracks(self, *args: str) -> None:
        self.imported.append(args)

    def all_folders(self) -> list[str]:
        return []

    def all_playlists(self) -> list[str]:
        return []


class TestImportTracks:
    def test_delegates_to_beets(self) -> None:
        beets = FakeBeets()
        service = LibraryService(beets, Settings())

        service.import_tracks("/path/to/music", "--flat")

        assert beets.imported == [("/path/to/music", "--flat")]


class TestRenameFolder:
    def test_updates_folder_and_genre_then_moves(self) -> None:
        beets = FakeBeets()
        beets._items = [
            {"id": "1", "path": "/music/old/a.mp3", "folder": "old", "genre": "old"},
            {"id": "2", "path": "/music/old/b.mp3", "folder": "old", "genre": "old"},
        ]
        service = LibraryService(beets, Settings())

        service.rename_folder("old", "new")

        assert len(beets.modifications) == 2
        for _, fields in beets.modifications:
            assert fields["folder"] == "new"
            assert fields["genre"] == "new"
        assert beets.moved == ["folder:new"]
