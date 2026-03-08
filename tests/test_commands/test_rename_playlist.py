import tempfile
from pathlib import Path
from unittest.mock import patch

from musictl.commands.rename_playlist import rename_playlist
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

    def query(self, query: str) -> list[dict[str, str]]:
        if query.startswith("playlists:"):
            target = query[len("playlists:") :]
            return [i for i in self._items if target in [p.strip() for p in i.get("playlists", "").split(",")]]
        return self._items

    def get_field(self, query: str, field: str) -> str:
        return ""

    def modify(self, query: str, **fields: str) -> None:
        self.modifications.append((query, fields))

    def move(self, query: str) -> None: ...
    def remove(self, query: str, delete: bool = False) -> None: ...
    def import_tracks(self, *args: str) -> None: ...
    def all_folders(self) -> list[str]:
        return []

    def all_playlists(self) -> list[str]:
        return []


class TestRenamePlaylistCommand:
    def test_renames_playlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            music_dir = Path(tmpdir) / "music"
            music_dir.mkdir()
            playlists_dir = Path(tmpdir) / "playlists"
            test_settings = Settings(music_dir=music_dir, playlists_dir=playlists_dir)
            mpd = FakeMpd()
            beets = FakeBeets()
            beets._items = [
                {"id": "1", "path": "/music/a.mp3", "folder": "rock", "playlists": "oldname,other"},
            ]

            with (
                patch("musictl.commands.rename_playlist.MpdAdapter", return_value=mpd),
                patch("musictl.commands.rename_playlist.BeetsAdapter", return_value=beets),
                patch("musictl.commands.rename_playlist.settings", test_settings),
            ):
                rename_playlist("oldname", "newname")

            assert len(beets.modifications) == 1
            _, fields = beets.modifications[0]
            assert fields["playlists"] == "newname,other"
            assert fields["comments"] == "playlists:newname,other"
