import tempfile
from pathlib import Path
from unittest.mock import patch

from musictl.commands.rename_folder import rename_folder
from musictl.config import Settings


class FakeMpd:
    def connect(self) -> None: ...
    def current_song(self) -> dict[str, str] | None:
        return None

    def add(self, uri: str) -> None: ...
    def play(self, pos: int = 0) -> None: ...
    def clear(self) -> None: ...
    def delete(self, pos: int) -> None: ...
    def load_playlist(self, name: str) -> None: ...
    def list_playlists(self) -> list[str]:
        return []

    def search(self, query: str) -> list[dict[str, str]]:
        return []

    def update(self) -> None: ...
    def current_position(self) -> int | None:
        return None

    def list_playlist_tracks(self, name: str) -> list[str]:
        return []

    def queue_count(self) -> int:
        return 0


class FakeBeets:
    def __init__(self) -> None:
        self._items: list[dict[str, str]] = []
        self.modifications: list[tuple[str, dict[str, str]]] = []
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
    def import_tracks(self, *args: str) -> None: ...
    def all_folders(self) -> list[str]:
        return []

    def all_playlists(self) -> list[str]:
        return []


class TestRenameFolderCommand:
    def test_renames_folder_and_regenerates_playlists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            music_dir = Path(tmpdir) / "music"
            music_dir.mkdir()
            playlists_dir = Path(tmpdir) / "playlists"
            test_settings = Settings(music_dir=music_dir, playlists_dir=playlists_dir)
            mpd = FakeMpd()
            beets = FakeBeets()
            beets._items = [
                {"id": "1", "path": "/music/old/a.mp3", "folder": "old", "genre": "old", "playlists": ""},
            ]

            with (
                patch("musictl.commands.rename_folder.BeetsAdapter", return_value=beets),
                patch("musictl.commands.rename_folder.MpdAdapter", return_value=mpd),
                patch("musictl.commands.rename_folder.settings", test_settings),
            ):
                rename_folder("old", "new")

            assert len(beets.modifications) == 1
            _, fields = beets.modifications[0]
            assert fields["folder"] == "new"
            assert fields["genre"] == "new"
            assert beets.moved == ["folder:new"]
