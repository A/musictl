from musictl.services.cue_split import CueSplitService


class FakeFfmpeg:
    def __init__(self, result: list[str] | None = None) -> None:
        self.calls: list[tuple[str, str, str]] = []
        self._result = result or []

    def split_cue(self, audio_file: str, cue_file: str, output_dir: str) -> list[str]:
        self.calls.append((audio_file, cue_file, output_dir))
        return self._result


class TestCueSplitService:
    def test_split_delegates_to_ffmpeg(self) -> None:
        ffmpeg = FakeFfmpeg(result=["/out/01.flac", "/out/02.flac"])
        service = CueSplitService(ffmpeg)

        result = service.split("/audio.flac", "/sheet.cue", "/out")

        assert result == ["/out/01.flac", "/out/02.flac"]
        assert ffmpeg.calls == [("/audio.flac", "/sheet.cue", "/out")]
