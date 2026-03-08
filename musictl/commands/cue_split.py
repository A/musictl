import cyclopts

from musictl.adapters.ffmpeg import FfmpegAdapter
from musictl.services.cue_split import CueSplitService

app = cyclopts.App(name="cue-split", help="Split audio file by CUE sheet")


@app.default
def cue_split(audio_file: str, *, cue: str, output_dir: str = ".") -> None:
    """Split an audio file into tracks using a CUE sheet."""
    ffmpeg = FfmpegAdapter()
    service = CueSplitService(ffmpeg)
    paths = service.split(audio_file, cue, output_dir)
    for path in paths:
        print(path)
