from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from musictl.adapters import beets as beets_mod
from musictl.adapters.beets import BeetsAdapter


@pytest.fixture
def beets():
    with patch("musictl.adapters.beets.Library") as mock_lib_cls:
        mock_lib = MagicMock()
        mock_lib_cls.return_value = mock_lib
        adapter = BeetsAdapter()
        adapter._lib = mock_lib
        yield adapter


def _make_item(**kwargs):
    item = MagicMock()
    item.id = kwargs.get("id", 1)
    item.path = kwargs.get("path", b"/music/test.mp3")
    item.artist = kwargs.get("artist", "Artist")
    item.title = kwargs.get("title", "Title")
    item.album = kwargs.get("album", "Album")
    item.genre = kwargs.get("genre", "Rock")
    item.folder = kwargs.get("folder", "rock")
    item.playlists = kwargs.get("playlists", "chill,workout")
    return item


class TestQuery:
    def test_returns_item_dicts(self, beets: BeetsAdapter):
        beets._lib.items.return_value = [_make_item()]

        result = beets.query("artist:Test")

        assert len(result) == 1
        assert result[0]["artist"] == "Artist"
        assert result[0]["folder"] == "rock"
        assert result[0]["playlists"] == "chill,workout"

    def test_returns_empty_list(self, beets: BeetsAdapter):
        beets._lib.items.return_value = []

        assert beets.query("nonexistent") == []

    def test_handles_missing_custom_fields(self, beets: BeetsAdapter):
        item = MagicMock(spec=["id", "path", "artist", "title", "album", "genre"])
        item.id = 1
        item.path = b"/music/test.mp3"
        item.artist = "Artist"
        item.title = "Title"
        item.album = "Album"
        item.genre = "Rock"
        beets._lib.items.return_value = [item]

        result = beets.query("")

        assert result[0]["folder"] == ""
        assert result[0]["playlists"] == ""


class TestPathQuery:
    """path: queries must match regardless of relative/absolute path form.

    Regression: beets stores paths relative to music_dir on some machines,
    while MPD reports absolute paths. Naive string equality misses these,
    leaving the current track un-enriched (no folder/playlists -> "Inbox").
    """

    @pytest.fixture(autouse=True)
    def _fixed_music_dir(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(beets_mod.settings, "music_dir", Path("/music"))

    def test_relative_db_path_matches_absolute_query(self, beets: BeetsAdapter):
        beets._lib.items.return_value = [
            _make_item(path=b"Ambient/Kavinsky & Lovefoxxx - Wrong Floor.flac", folder="Ambient"),
        ]

        result = beets.query("path:/music/Ambient/Kavinsky & Lovefoxxx - Wrong Floor.flac")

        assert len(result) == 1
        assert result[0]["folder"] == "Ambient"
        assert result[0]["path"] == "/music/Ambient/Kavinsky & Lovefoxxx - Wrong Floor.flac"

    def test_absolute_db_path_matches_absolute_query(self, beets: BeetsAdapter):
        beets._lib.items.return_value = [
            _make_item(path=b"/music/Ambient/Wrong Floor.flac", folder="Ambient"),
        ]

        result = beets.query("path:/music/Ambient/Wrong Floor.flac")

        assert len(result) == 1
        assert result[0]["folder"] == "Ambient"

    def test_no_match_returns_empty(self, beets: BeetsAdapter):
        beets._lib.items.return_value = [_make_item(path=b"Ambient/Other.flac")]

        assert beets.query("path:/music/Ambient/Missing.flac") == []


class TestGetField:
    def test_returns_field_value(self, beets: BeetsAdapter):
        beets._lib.items.return_value = [_make_item(genre="Jazz")]

        assert beets.get_field("id:1", "genre") == "Jazz"

    def test_returns_empty_when_no_match(self, beets: BeetsAdapter):
        beets._lib.items.return_value = []

        assert beets.get_field("id:999", "genre") == ""


class TestSubprocessCommands:
    def test_modify(self, beets: BeetsAdapter):
        with patch("musictl.adapters.beets.subprocess.run") as mock_run:
            beets.modify("id:1", folder="jazz", genre="Jazz")
            mock_run.assert_called_once_with(
                ["beet", "modify", "-y", "-m", "id:1", "folder=jazz", "genre=Jazz"],
                check=True,
            )

    def test_move(self, beets: BeetsAdapter):
        with patch("musictl.adapters.beets.subprocess.run") as mock_run:
            beets.move("id:1")
            mock_run.assert_called_once_with(["beet", "move", "id:1"], check=True)

    def test_remove(self, beets: BeetsAdapter):
        with patch("musictl.adapters.beets.subprocess.run") as mock_run:
            beets.remove("id:1", delete=True)
            mock_run.assert_called_once_with(["beet", "remove", "-d", "-f", "id:1"], check=True)

    def test_remove_without_delete(self, beets: BeetsAdapter):
        with patch("musictl.adapters.beets.subprocess.run") as mock_run:
            beets.remove("id:1")
            mock_run.assert_called_once_with(["beet", "remove", "-f", "id:1"], check=True)

    def test_import_tracks(self, beets: BeetsAdapter):
        with patch("musictl.adapters.beets.subprocess.run") as mock_run:
            beets.import_tracks("/music/inbox", "--quiet")
            mock_run.assert_called_once_with(["beet", "import", "/music/inbox", "--quiet"], check=True)


class TestCollections:
    def test_all_folders(self, beets: BeetsAdapter):
        beets._lib.items.return_value = [
            _make_item(folder="rock"),
            _make_item(folder="jazz"),
            _make_item(folder="rock"),
            _make_item(folder=""),
        ]

        result = beets.all_folders()

        assert result == ["jazz", "rock"]

    def test_all_playlists(self, beets: BeetsAdapter):
        beets._lib.items.return_value = [
            _make_item(playlists="chill,workout"),
            _make_item(playlists="workout,focus"),
            _make_item(playlists=""),
        ]

        result = beets.all_playlists()

        assert result == {"chill": 1, "focus": 1, "workout": 2}
