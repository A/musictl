import pytest

from musictl.adapters.beets import BeetsAdapter, _item_path
from musictl.config import Settings
from musictl.services.tracks import TrackService
from tests.conftest import BeetsEnv, assert_isolated
from tests.support.seeding import seed_item


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

    def all_playlists(self) -> dict[str, int]:
        return {}

    def remove(self, query: str, delete: bool = False) -> None:
        self.removed.append((query, delete))


class FakeDialog:
    def __init__(self, confirm_result: bool = True) -> None:
        self._confirm_result = confirm_result

    def confirm(self, title: str, text: str) -> bool:
        return self._confirm_result

    def form(
        self,
        title: str,
        fields: list[str],
        values: list[str] | None = None,
        text: str | None = None,
        columns: int = 1,
    ) -> list[str] | None:
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


@pytest.mark.e2e
def test_current_track_enriches_relative_path(
    beets_adapter: BeetsAdapter,
    tmp_settings: Settings,
    beets_env: BeetsEnv,
) -> None:
    """Inbox-bug regression at the service seam: a fake MPD reports a
    music_dir-relative `file` while a real seeded beets library stores the path
    in a version-dependent form (2.12 absolutizes against the library
    `directory`, which the fixture sets != music_dir). `current_track` must
    still enrich folder/playlists; the original bug's naive string compare left
    them empty and waybar rendered every track as "Inbox". The matching waybar
    Pango-escaping regression is covered by tests/test_commands/test_waybar.py.
    """
    assert_isolated(beets_env)
    rel = "Ambient/Kavinsky & Lovefoxxx - Wrong Floor.flac"
    item = seed_item(beets_adapter._lib, path=rel, folder="Ambient", playlists="drive")

    # Discriminating check: the raw reported path does NOT string-equal the
    # absolute MPD-constructed path, so a naive string compare in `query` would
    # leave the track un-enriched. This is exactly the bug condition, so the
    # test fails if path-matching regresses to a naive compare.
    abs_mpd_path = str(tmp_settings.music_dir / rel)
    assert _item_path(item) != abs_mpd_path

    mpd = FakeMpd()
    mpd._current_song = {"file": rel}
    service = TrackService(mpd, beets_adapter, tmp_settings)

    result = service.current_track()
    assert result is not None
    assert result["folder"] == "Ambient"
    assert result["playlists"] == "drive"


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
        assert mpd.deleted == [3]
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
