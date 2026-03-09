from unittest.mock import MagicMock, patch

from musictl.adapters.tagger import TaggerAdapter


@patch("musictl.adapters.tagger.File")
class TestReadTags:
    def test_reads_available_tags(self, mock_file):
        audio = MagicMock()
        audio.get.side_effect = lambda key: {"artist": ["The Band"], "album": ["Album X"], "genre": ["Rock"]}.get(key)
        mock_file.return_value = audio

        result = TaggerAdapter().read_tags("/music/track.mp3")

        mock_file.assert_called_once_with("/music/track.mp3", easy=True)
        assert result == {"artist": "The Band", "album": "Album X", "genre": "Rock"}

    def test_returns_empty_dict_for_unsupported_file(self, mock_file):
        mock_file.return_value = None

        assert TaggerAdapter().read_tags("/music/track.xyz") == {}

    def test_skips_missing_tags(self, mock_file):
        audio = MagicMock()
        audio.get.side_effect = lambda key: {"artist": ["Solo"]}.get(key)
        mock_file.return_value = audio

        result = TaggerAdapter().read_tags("/music/track.flac")

        assert result == {"artist": "Solo"}


@patch("musictl.adapters.tagger.File")
class TestWriteTags:
    def test_writes_tags_and_saves(self, mock_file):
        audio = MagicMock()
        mock_file.return_value = audio

        TaggerAdapter().write_tags("/music/track.mp3", {"artist": "New", "genre": "Jazz"})

        mock_file.assert_called_once_with("/music/track.mp3", easy=True)
        audio.__setitem__.assert_any_call("artist", "New")
        audio.__setitem__.assert_any_call("genre", "Jazz")
        audio.save.assert_called_once()

    def test_noop_for_unsupported_file(self, mock_file):
        mock_file.return_value = None

        TaggerAdapter().write_tags("/music/track.xyz", {"artist": "X"})
