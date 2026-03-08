from unittest.mock import MagicMock, patch

from musictl.adapters.ffmpeg import FfmpegAdapter


class TestSplitCue:
    def test_splits_and_returns_output_files(self, tmp_path):
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        (out_dir / "01 - Track One.flac").touch()
        (out_dir / "02 - Track Two.flac").touch()

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
            result = adapter.split_cue("audio.flac", "audio.cue", str(out_dir))

        mock_cls.assert_called_once_with(filename="audio.cue", outputdir=str(out_dir))
        mock_splitter.open_cuefile.assert_called_once()
        mock_splitter.commandargs.assert_called_once_with(mock_splitter.audiotracks)
        assert len(result) == 2
        assert any("Track One" in p for p in result)
        assert any("Track Two" in p for p in result)
