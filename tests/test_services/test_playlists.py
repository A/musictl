import tempfile
from pathlib import Path

from musictl.config import Settings
from musictl.services.playlists import PlaylistService


class FakeMpd:
    def __init__(self) -> None:
        self.cleared: bool = False
        self.loaded: list[str] = []

    def connect(self) -> None: ...
    def current_song(self) -> dict[str, str] | None:
        return None

    def add(self, uri: str) -> None: ...
    def play(self, pos: int = 0) -> None: ...
    def delete(self, pos: int) -> None: ...
    def list_playlists(self) -> list[str]:
        return []

    def search(self, query: str) -> list[dict[str, str]]:
        return []

    def update(self) -> None: ...
    def current_position(self) -> int | None:
        return None

    def queue_count(self) -> int:
        return 0

    def clear(self) -> None:
        self.cleared = True

    def load_playlist(self, name: str) -> None:
        self.loaded.append(name)


class FakeBeets:
    def __init__(self) -> None:
        self._items: list[dict[str, str]] = []
        self.modifications: list[tuple[str, dict[str, str]]] = []

    def query(self, query: str) -> list[dict[str, str]]:
        if query.startswith("playlists:"):
            target = query[len("playlists:") :]
            return [i for i in self._items if target in [p.strip() for p in i.get("playlists", "").split(",")]]
        if query.startswith("folder:"):
            target = query[len("folder:") :]
            return [i for i in self._items if i.get("folder", "") == target]
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

    def random(self, count: int, query: str = "") -> list[str]:
        return []


class TestLoad:
    def test_clears_and_loads(self) -> None:
        mpd = FakeMpd()
        beets = FakeBeets()
        settings = Settings()
        service = PlaylistService(mpd, beets, settings)

        service.load("rock")

        assert mpd.cleared is True
        assert mpd.loaded == ["rock"]


class TestGenerateAll:
    def test_generates_inbox_for_tracks_without_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            music_dir = Path(tmpdir) / "music"
            music_dir.mkdir()
            playlists_dir = Path(tmpdir) / "playlists"
            settings = Settings(music_dir=music_dir, playlists_dir=playlists_dir)
            mpd = FakeMpd()
            beets = FakeBeets()
            beets._items = [
                {"path": str(music_dir / "new_track.mp3"), "folder": "", "playlists": ""},
            ]
            service = PlaylistService(mpd, beets, settings)

            written = service.generate_all()

            assert len(written) == 2  # inbox + all
            content = (playlists_dir / "inbox.m3u").read_text()
            assert "new_track.mp3" in content
            assert (playlists_dir / "all.m3u").exists()

    def test_generates_folder_playlists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            music_dir = Path(tmpdir) / "music"
            music_dir.mkdir()
            playlists_dir = Path(tmpdir) / "playlists"
            settings = Settings(music_dir=music_dir, playlists_dir=playlists_dir)
            mpd = FakeMpd()
            beets = FakeBeets()
            beets._items = [
                {"path": str(music_dir / "rock/a.mp3"), "folder": "rock", "playlists": "chill"},
                {"path": str(music_dir / "rock/b.mp3"), "folder": "rock", "playlists": ""},
            ]
            service = PlaylistService(mpd, beets, settings)

            service.generate_all()

            # folder playlist
            rock_content = (playlists_dir / "rock.m3u").read_text()
            assert "rock/a.mp3" in rock_content
            assert "rock/b.mp3" in rock_content

            # named playlist
            chill_content = (playlists_dir / "playlist_chill.m3u").read_text()
            assert "rock/a.mp3" in chill_content

            # no_playlist
            no_pl_content = (playlists_dir / "no_playlist.m3u").read_text()
            assert "rock/b.mp3" in no_pl_content

            # collection (all non-inbox)
            collection_content = (playlists_dir / "collection.m3u").read_text()
            assert "rock/a.mp3" in collection_content
            assert "rock/b.mp3" in collection_content

            # all tracks
            all_content = (playlists_dir / "all.m3u").read_text()
            assert "rock/a.mp3" in all_content

    def test_handles_multiple_comma_separated_playlists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            music_dir = Path(tmpdir) / "music"
            music_dir.mkdir()
            playlists_dir = Path(tmpdir) / "playlists"
            settings = Settings(music_dir=music_dir, playlists_dir=playlists_dir)
            mpd = FakeMpd()
            beets = FakeBeets()
            beets._items = [
                {"path": str(music_dir / "t.mp3"), "folder": "jazz", "playlists": "chill,focus"},
            ]
            service = PlaylistService(mpd, beets, settings)

            service.generate_all()

            assert (playlists_dir / "playlist_chill.m3u").exists()
            assert (playlists_dir / "playlist_focus.m3u").exists()


class TestRename:
    def test_renames_playlist_and_syncs_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            music_dir = Path(tmpdir) / "music"
            music_dir.mkdir()
            playlists_dir = Path(tmpdir) / "playlists"
            settings = Settings(music_dir=music_dir, playlists_dir=playlists_dir)
            mpd = FakeMpd()
            beets = FakeBeets()
            beets._items = [
                {"path": "/music/a.mp3", "folder": "rock", "playlists": "old_name,other"},
            ]
            service = PlaylistService(mpd, beets, settings)

            service.rename("old_name", "new_name")

            assert len(beets.modifications) == 1
            query, fields = beets.modifications[0]
            assert query == "path:/music/a.mp3"
            assert fields["playlists"] == "new_name,other"
            assert fields["comments"] == "playlists:new_name,other"
