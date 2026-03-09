import logging
from pathlib import Path

from ffcuesplitter.cuesplitter import FFCueSplitter

logger = logging.getLogger(__name__)


class FfmpegAdapter:
    def parse_cue(self, cue_file: str) -> list[dict[str, str]]:
        logger.info("Parsing CUE %s", cue_file)
        splitter = FFCueSplitter(filename=cue_file)
        splitter.open_cuefile()
        return [{k: str(v) for k, v in track.items()} for track in splitter.audiotracks]

    def split_cue(
        self,
        audio_file: str,
        cue_file: str,
        output_dir: str,
        *,
        artist: str | None = None,
        album: str | None = None,
    ) -> list[str]:
        logger.info("Splitting %s with CUE %s -> %s", audio_file, cue_file, output_dir)
        splitter = FFCueSplitter(filename=cue_file, outputdir=output_dir)
        splitter.open_cuefile()
        tracks = splitter.audiotracks
        for track in tracks:
            if artist is not None:
                track["PERFORMER"] = artist
            if album is not None:
                track["ALBUM"] = album
        recipes = splitter.commandargs(tracks)
        for cmd, info in recipes["recipes"]:
            splitter.command_runner(cmd, info["duration"])
        return [str(p) for p in Path(output_dir).iterdir() if p.is_file()]
