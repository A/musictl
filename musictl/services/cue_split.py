from musictl.protocols import FfmpegBackend


class CueSplitService:
    def __init__(self, ffmpeg: FfmpegBackend) -> None:
        self._ffmpeg = ffmpeg

    def split(self, audio_file: str, cue_file: str, output_dir: str) -> list[str]:
        return self._ffmpeg.split_cue(audio_file, cue_file, output_dir)
