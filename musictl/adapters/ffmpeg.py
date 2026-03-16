import logging
from pathlib import Path
from typing import Any

from ffcuesplitter.cuesplitter import FFCueSplitter
from ffcuesplitter.exceptions import FFProbeError
from ffcuesplitter.ffmpeg import FFMpeg

logger = logging.getLogger(__name__)


def _create_splitter(cue_file: str, **kwargs: Any) -> FFCueSplitter:
    try:
        return FFCueSplitter(filename=cue_file, **kwargs)
    except FFProbeError as e:
        msg = (
            f"Failed to probe audio for '{cue_file}': {e}\n"
            "Hint: the file may have corrupt metadata (e.g. broken embedded artwork). "
            "Try stripping it with: metaflac --remove --block-type=PICTURE <file>"
        )
        raise RuntimeError(msg) from e


class FfmpegAdapter:
    def parse_cue(self, cue_file: str) -> list[dict[str, str]]:
        logger.info("Parsing CUE %s", cue_file)
        splitter = _create_splitter(cue_file)
        return [{k: str(v) for k, v in track.items()} for track in splitter.audiotracks]

    def split_cue(
        self,
        cue_file: str,
        output_dir: str,
        *,
        artist: str | None = None,
        album: str | None = None,
    ) -> list[str]:
        logger.info("Splitting CUE %s -> %s", cue_file, output_dir)

        original_codec = FFMpeg.DATACODECS.get("flac")
        FFMpeg.DATACODECS["flac"] = "flac"

        try:
            splitter = _create_splitter(
                cue_file,
                outputdir=output_dir,
                outputformat="flac",
            )
            tracks = splitter.audiotracks
            for track in tracks:
                if artist is not None:
                    track["PERFORMER"] = artist
                if album is not None:
                    track["ALBUM"] = album
            recipes = splitter.commandargs(tracks)
            output_names: list[str] = []
            for cmd, info in recipes["recipes"]:
                splitter.command_runner(cmd, info["duration"])
                output_names.append(info["titletrack"])
        finally:
            if original_codec is not None:
                FFMpeg.DATACODECS["flac"] = original_codec

        return [str(Path(output_dir) / name) for name in output_names]
