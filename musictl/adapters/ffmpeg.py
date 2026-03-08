import logging
from pathlib import Path

from ffcuesplitter.cuesplitter import FFCueSplitter

logger = logging.getLogger(__name__)


class FfmpegAdapter:
    def split_cue(self, audio_file: str, cue_file: str, output_dir: str) -> list[str]:
        logger.info("Splitting %s with CUE %s -> %s", audio_file, cue_file, output_dir)
        splitter = FFCueSplitter(filename=cue_file, outputdir=output_dir)
        splitter.open_cuefile()
        tracks = splitter.audiotracks
        recipes = splitter.commandargs(tracks)
        for cmd, info in recipes["recipes"]:
            splitter.command_runner(cmd, info["duration"])
        return [str(p) for p in Path(output_dir).iterdir() if p.is_file()]
