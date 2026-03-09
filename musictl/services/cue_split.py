from musictl.protocols import FfmpegBackend


class CueSplitService:
    def __init__(self, ffmpeg: FfmpegBackend) -> None:
        self._ffmpeg = ffmpeg

    def parse(self, cue_file: str) -> list[dict[str, str]]:
        return self._ffmpeg.parse_cue(cue_file)

    def split(
        self,
        audio_file: str,
        cue_file: str,
        output_dir: str,
        *,
        artist: str | None = None,
        album: str | None = None,
    ) -> list[str]:
        return self._ffmpeg.split_cue(audio_file, cue_file, output_dir, artist=artist, album=album)
