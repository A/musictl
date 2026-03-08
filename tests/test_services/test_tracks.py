from musictl.config import Settings
from musictl.services.tracks import TrackService


class FakeMpd:
    def __init__(self) -> None:
        self._current_song: dict[str, str] | None = None
        self._position: int | None = None
        self.deleted: list[int] = []
        self.updated: bool = False

    def connect(self) -> None: ...
    def add(self, uri: str) -> None: ...
    def play(self, pos: int = 0) -> None: ...
    def clear(self) -> None: ...
    def load_playlist(self, name: str) -> None: ...
    def list_playlists(self) -> list[str]:
        return []

    def search(self, query: str) -> list[dict[str, str]]:
        return []

    def list_playlist_tracks(self, name: str) -> list[str]:
        return []

    def queue_count(self) -> int:
        return 0

    def current_song(self) -> dict[str, str] | None:
        return self._current_song

    def current_position(self) -> int | None:
        return self._position

    def delete(self, pos: int) -> None:
        self.deleted.append(pos)

    def update(self) -> None:
        self.updated = True


class FakeBeets:
    def __init__(self) -> None:
        self._items: list[dict[str, str]] = []
        self.removed: list[tuple[str, bool]] = []

    def query(self, query: str) -> list[dict[str, str]]:
        if query.startswith("path:"):
            path = query[5:]
            return [i for i in self._items if i.get("path") == path]
        return self._items

    def get_field(self, query: str, field: str) -> str:
        return ""

    def modify(self, query: str, **fields: str) -> None: ...
    def move(self, query: str) -> None: ...
    def import_tracks(self, *args: str) -> None: ...
    def all_folders(self) -> list[str]:
        return []

    def all_playlists(self) -> list[str]:
        return []

    def remove(self, query: str, delete: bool = False) -> None:
        self.removed.append((query, delete))


class FakeDialog:
    def __init__(self, confirm_result: bool = True) -> None:
        self._confirm_result = confirm_result

    def confirm(self, title: str, text: str) -> bool:
        return self._confirm_result

    def form(self, title: str, fields: list[str], values: list[str] | None = None) -> list[str] | None:
        return None

    def notify(self, title: str, text: str) -> None: ...


def _settings() -> Settings:
    return Settings(music_dir=Settings().music_dir)


class TestCurrentTrack:
    def test_returns_none_when_nothing_playing(self) -> None:
        mpd = FakeMpd()
        beets = FakeBeets()
        service = TrackService(mpd, beets, _settings())

        assert service.current_track() is None

    def test_returns_song_without_beets_enrichment(self) -> None:
        mpd = FakeMpd()
        mpd._current_song = {"file": "some/track.mp3", "title": "Test"}
        beets = FakeBeets()
        service = TrackService(mpd, beets, _settings())

        result = service.current_track()
        assert result is not None
        assert result["title"] == "Test"

    def test_enriches_with_beets_data(self) -> None:
        mpd = FakeMpd()
        mpd._current_song = {"file": "rock/track.mp3"}
        beets = FakeBeets()
        full_path = str(Settings().music_dir / "rock/track.mp3")
        beets._items = [{"path": full_path, "artist": "Band", "title": "Song", "folder": "rock", "playlists": ""}]
        service = TrackService(mpd, beets, _settings())

        result = service.current_track()
        assert result is not None
        assert result["artist"] == "Band"
        assert result["folder"] == "rock"


class TestSearch:
    def test_delegates_to_beets(self) -> None:
        mpd = FakeMpd()
        beets = FakeBeets()
        beets._items = [{"path": "/a.mp3", "title": "Found"}]
        service = TrackService(mpd, beets, _settings())

        result = service.search("title:Found")
        assert len(result) == 1
        assert result[0]["title"] == "Found"


class TestDeleteCurrent:
    def test_deletes_when_confirmed(self) -> None:
        mpd = FakeMpd()
        mpd._current_song = {"file": "track.mp3", "title": "Song", "artist": "Artist"}
        mpd._position = 3
        beets = FakeBeets()
        full_path = str(Settings().music_dir / "track.mp3")
        beets._items = [{"id": "42", "path": full_path, "title": "Song", "artist": "Artist"}]
        dialog = FakeDialog(confirm_result=True)
        service = TrackService(mpd, beets, _settings())

        assert service.delete_current(dialog) is True
        assert beets.removed == [("id:42", True)]
        assert mpd.deleted == []
        assert mpd.updated is True

    def test_aborts_when_not_confirmed(self) -> None:
        mpd = FakeMpd()
        mpd._current_song = {"file": "track.mp3", "title": "Song", "artist": "Artist"}
        beets = FakeBeets()
        dialog = FakeDialog(confirm_result=False)
        service = TrackService(mpd, beets, _settings())

        assert service.delete_current(dialog) is False
        assert beets.removed == []

    def test_returns_false_when_nothing_playing(self) -> None:
        mpd = FakeMpd()
        beets = FakeBeets()
        dialog = FakeDialog()
        service = TrackService(mpd, beets, _settings())

        assert service.delete_current(dialog) is False


class TestCleanCurrent:
    def test_removes_current_from_queue(self) -> None:
        mpd = FakeMpd()
        mpd._position = 5
        beets = FakeBeets()
        service = TrackService(mpd, beets, _settings())

        assert service.clean_current() is True
        assert mpd.deleted == [5]

    def test_returns_false_when_nothing_playing(self) -> None:
        mpd = FakeMpd()
        beets = FakeBeets()
        service = TrackService(mpd, beets, _settings())

        assert service.clean_current() is False
