from unittest.mock import MagicMock, patch

import pytest
from mpd import ConnectionError as MpdConnectionError

from musictl.adapters.mpd import MpdAdapter


@pytest.fixture
def mpd():
    with patch("musictl.adapters.mpd.MPDClient") as mock_cls:
        adapter = MpdAdapter()
        adapter._client = mock_cls.return_value
        yield adapter


class TestConnect:
    def test_connects_to_mpd(self, mpd: MpdAdapter):
        mpd.connect()
        mpd._client.connect.assert_called_once()

    def test_does_not_reconnect_if_already_connected(self, mpd: MpdAdapter):
        mpd.connect()
        mpd.connect()
        mpd._client.connect.assert_called_once()


class TestAutoReconnect:
    def test_reconnects_on_connection_error(self, mpd: MpdAdapter):
        mpd._connected = True
        mpd._client.ping.side_effect = MpdConnectionError("lost")

        with patch("musictl.adapters.mpd.MPDClient") as new_cls:
            new_client = MagicMock()
            new_cls.return_value = new_client
            mpd.current_song()

        new_client.connect.assert_called_once()
        new_client.currentsong.assert_called_once()


class TestCurrentSong:
    def test_returns_song_dict(self, mpd: MpdAdapter):
        mpd._client.currentsong.return_value = {"file": "test.mp3", "artist": "Test"}
        mpd._connected = True

        result = mpd.current_song()

        assert result == {"file": "test.mp3", "artist": "Test"}

    def test_returns_none_when_no_song(self, mpd: MpdAdapter):
        mpd._client.currentsong.return_value = {}
        mpd._connected = True

        assert mpd.current_song() is None


class TestQueueOperations:
    def test_add(self, mpd: MpdAdapter):
        mpd._connected = True
        mpd.add("test.mp3")
        mpd._client.add.assert_called_once_with("test.mp3")

    def test_play(self, mpd: MpdAdapter):
        mpd._connected = True
        mpd.play(3)
        mpd._client.play.assert_called_once_with(3)

    def test_clear(self, mpd: MpdAdapter):
        mpd._connected = True
        mpd.clear()
        mpd._client.clear.assert_called_once()

    def test_delete(self, mpd: MpdAdapter):
        mpd._connected = True
        mpd.delete(5)
        mpd._client.delete.assert_called_once_with(5)


class TestPlaylists:
    def test_load_playlist(self, mpd: MpdAdapter):
        mpd._connected = True
        mpd.load_playlist("rock")
        mpd._client.load.assert_called_once_with("rock")

    def test_list_playlists(self, mpd: MpdAdapter):
        mpd._connected = True
        mpd._client.listplaylists.return_value = [
            {"playlist": "rock"},
            {"playlist": "jazz"},
        ]

        result = mpd.list_playlists()

        assert result == ["rock", "jazz"]


class TestSearch:
    def test_search(self, mpd: MpdAdapter):
        mpd._connected = True
        mpd._client.search.return_value = [{"file": "a.mp3"}]

        result = mpd.search("test")

        mpd._client.search.assert_called_once_with("any", "test")
        assert result == [{"file": "a.mp3"}]


class TestStatus:
    def test_current_position(self, mpd: MpdAdapter):
        mpd._connected = True
        mpd._client.status.return_value = {"song": "3"}

        assert mpd.current_position() == 3

    def test_current_position_none(self, mpd: MpdAdapter):
        mpd._connected = True
        mpd._client.status.return_value = {}

        assert mpd.current_position() is None

    def test_queue_count(self, mpd: MpdAdapter):
        mpd._connected = True
        mpd._client.status.return_value = {"playlistlength": "42"}

        assert mpd.queue_count() == 42

    def test_queue_count_empty(self, mpd: MpdAdapter):
        mpd._connected = True
        mpd._client.status.return_value = {}

        assert mpd.queue_count() == 0
