from musictl.services.cue_split import CueSplitService


class FakeFfmpeg:
    def __init__(self, result: list[str] | None = None, tracks: list[dict[str, str]] | None = None) -> None:
        self.split_calls: list[tuple[str, str, str | None, str | None]] = []
        self.parse_calls: list[str] = []
        self._result = result or []
        self._tracks = tracks or []

    def parse_cue(self, cue_file: str) -> list[dict[str, str]]:
        self.parse_calls.append(cue_file)
        return self._tracks

    def split_cue(
        self,
        cue_file: str,
        output_dir: str,
        *,
        artist: str | None = None,
        album: str | None = None,
    ) -> list[str]:
        self.split_calls.append((cue_file, output_dir, artist, album))
        return self._result


class TestCueSplitService:
    def test_split_delegates_to_ffmpeg(self) -> None:
        ffmpeg = FakeFfmpeg(result=["/out/01.flac", "/out/02.flac"])
        service = CueSplitService(ffmpeg)

        result = service.split("/sheet.cue", "/out")

        assert result == ["/out/01.flac", "/out/02.flac"]
        assert ffmpeg.split_calls == [("/sheet.cue", "/out", None, None)]

    def test_split_passes_artist_album(self) -> None:
        ffmpeg = FakeFfmpeg(result=["/out/01.flac"])
        service = CueSplitService(ffmpeg)

        service.split("/sheet.cue", "/out", artist="Artist", album="Album")

        assert ffmpeg.split_calls == [("/sheet.cue", "/out", "Artist", "Album")]

    def test_parse_delegates_to_ffmpeg(self) -> None:
        tracks = [{"PERFORMER": "Artist", "ALBUM": "Album", "TITLE": "Track", "TRACK_NUM": "1"}]
        ffmpeg = FakeFfmpeg(tracks=tracks)
        service = CueSplitService(ffmpeg)

        result = service.parse("/sheet.cue")

        assert result == tracks
        assert ffmpeg.parse_calls == ["/sheet.cue"]
