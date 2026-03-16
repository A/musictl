from unittest.mock import MagicMock, patch

import pytest
from ffcuesplitter.exceptions import FFProbeError
from ffcuesplitter.ffmpeg import FFMpeg

from musictl.adapters.ffmpeg import FfmpegAdapter


class TestParseCue:
    def test_returns_track_metadata(self):
        with patch("musictl.adapters.ffmpeg.FFCueSplitter") as mock_cls:
            mock_splitter = MagicMock()
            mock_cls.return_value = mock_splitter
            mock_splitter.audiotracks = [
                {"PERFORMER": "Artist", "ALBUM": "Album", "TITLE": "Track One", "TRACK_NUM": 1},
                {"PERFORMER": "Artist", "ALBUM": "Album", "TITLE": "Track Two", "TRACK_NUM": 2},
            ]

            adapter = FfmpegAdapter()
            result = adapter.parse_cue("audio.cue")

        mock_cls.assert_called_once_with(filename="audio.cue")
        assert result == [
            {"PERFORMER": "Artist", "ALBUM": "Album", "TITLE": "Track One", "TRACK_NUM": "1"},
            {"PERFORMER": "Artist", "ALBUM": "Album", "TITLE": "Track Two", "TRACK_NUM": "2"},
        ]

    def test_raises_runtime_error_on_ffprobe_failure(self):
        with patch("musictl.adapters.ffmpeg.FFCueSplitter") as mock_cls:
            mock_cls.side_effect = FFProbeError("Attached picture metadata block too short")

            adapter = FfmpegAdapter()
            with pytest.raises(RuntimeError, match="Failed to probe audio"):
                adapter.parse_cue("audio.cue")


class TestSplitCue:
    def test_splits_and_returns_output_files(self, tmp_path):
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        with patch("musictl.adapters.ffmpeg.FFCueSplitter") as mock_cls:
            mock_splitter = MagicMock()
            mock_cls.return_value = mock_splitter
            mock_splitter.audiotracks = [{"TRACK_NUM": 1}, {"TRACK_NUM": 2}]
            mock_splitter.commandargs.return_value = {
                "recipes": [
                    ("ffmpeg -i ...", {"duration": 180, "titletrack": "01 - Track One.flac"}),
                    ("ffmpeg -i ...", {"duration": 240, "titletrack": "02 - Track Two.flac"}),
                ]
            }

            adapter = FfmpegAdapter()
            result = adapter.split_cue("audio.cue", str(out_dir))

        mock_cls.assert_called_once_with(
            filename="audio.cue",
            outputdir=str(out_dir),
            outputformat="flac",
        )
        mock_splitter.commandargs.assert_called_once_with(mock_splitter.audiotracks)
        assert len(result) == 2
        assert any("Track One" in p for p in result)
        assert any("Track Two" in p for p in result)

    def test_patches_datacodecs_to_preserve_sample_rate(self, tmp_path):
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        original_codec = FFMpeg.DATACODECS["flac"]

        with patch("musictl.adapters.ffmpeg.FFCueSplitter") as mock_cls:
            mock_splitter = MagicMock()
            mock_cls.return_value = mock_splitter
            mock_splitter.audiotracks = [{"TRACK_NUM": 1}]
            mock_splitter.commandargs.return_value = {
                "recipes": [
                    ("ffmpeg -i ...", {"duration": 180, "titletrack": "01 - Track One.flac"}),
                ]
            }

            adapter = FfmpegAdapter()
            adapter.split_cue("audio.cue", str(out_dir))

        # DATACODECS restored after call
        assert FFMpeg.DATACODECS["flac"] == original_codec

    def test_restores_datacodecs_on_error(self):
        original_codec = FFMpeg.DATACODECS["flac"]

        with (
            patch("musictl.adapters.ffmpeg.FFCueSplitter") as mock_cls,
            pytest.raises(RuntimeError),
        ):
            mock_cls.side_effect = FFProbeError("fail")

            adapter = FfmpegAdapter()
            adapter.split_cue("audio.cue", "/tmp/out")

        assert FFMpeg.DATACODECS["flac"] == original_codec

    def test_split_with_artist_album_overrides(self, tmp_path):
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        with patch("musictl.adapters.ffmpeg.FFCueSplitter") as mock_cls:
            mock_splitter = MagicMock()
            mock_cls.return_value = mock_splitter
            mock_splitter.audiotracks = [
                {"TRACK_NUM": 1, "PERFORMER": "Unknown", "ALBUM": "Unknown"},
            ]
            mock_splitter.commandargs.return_value = {
                "recipes": [
                    ("ffmpeg -i ...", {"duration": 180, "titletrack": "01 - Track One.flac"}),
                ]
            }

            adapter = FfmpegAdapter()
            adapter.split_cue(
                "audio.cue",
                str(out_dir),
                artist="Real Artist",
                album="Real Album",
            )

        tracks_passed = mock_splitter.commandargs.call_args[0][0]
        assert tracks_passed[0]["PERFORMER"] == "Real Artist"
        assert tracks_passed[0]["ALBUM"] == "Real Album"
