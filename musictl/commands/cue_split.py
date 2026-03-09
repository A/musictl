import sys

import cyclopts

from musictl.adapters.ffmpeg import FfmpegAdapter
from musictl.adapters.yad import YadAdapter
from musictl.services.cue_split import CueSplitService

app = cyclopts.App(name="cue-split", help="Split audio file by CUE sheet")


@app.default
def cue_split(audio_file: str, *, cue: str, output_dir: str = ".") -> None:
    """Split an audio file into tracks using a CUE sheet."""
    ffmpeg = FfmpegAdapter()
    dialog = YadAdapter()
    service = CueSplitService(ffmpeg)

    try:
        tracks = service.parse(cue)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    artist = tracks[0].get("PERFORMER", "Unknown") if tracks else "Unknown"
    album = tracks[0].get("ALBUM", "Unknown") if tracks else "Unknown"

    track_lines = "\n".join(f"{t.get('TRACK_NUM', '?')}. {t.get('TITLE', 'Unknown')}" for t in tracks)

    result = dialog.form(
        title="Confirm CUE Split",
        fields=["Artist", "Album"],
        values=[artist, album],
        text=track_lines,
    )
    if result is None:
        sys.exit(1)

    artist, album = result[0], result[1]

    try:
        paths = service.split(audio_file, cue, output_dir, artist=artist, album=album)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    for path in paths:
        print(path)
