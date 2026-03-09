import logging
import subprocess
from pathlib import Path

from ffcuesplitter.cuesplitter import FFCueSplitter
from ffcuesplitter.exceptions import FFProbeError
from ffcuesplitter.ffmpeg import FFMpeg

logger = logging.getLogger(__name__)


def _open_cue(splitter: FFCueSplitter, cue_file: str) -> None:
    try:
        splitter.open_cuefile()
    except FFProbeError as e:
        msg = (
            f"Failed to probe audio for '{cue_file}': {e}\n"
            "Hint: the file may have corrupt metadata (e.g. broken embedded artwork). "
            "Try stripping it with: metaflac --remove --block-type=PICTURE <file>"
        )
        raise RuntimeError(msg) from e


def _remux(path: Path) -> None:
    """Remux a file in-place to fix duration metadata after stream-copy."""
    tmp = path.with_suffix(".remux" + path.suffix)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-c:a", "copy", str(tmp)],
        check=True,
    )
    tmp.replace(path)


class FfmpegAdapter:
    def parse_cue(self, cue_file: str) -> list[dict[str, str]]:
        logger.info("Parsing CUE %s", cue_file)
        splitter = FFCueSplitter(filename=cue_file)
        _open_cue(splitter, cue_file)
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
        ext = Path(audio_file).suffix.lower()
        is_flac = ext == ".flac"

        original_codec = FFMpeg.DATACODECS.get("flac")
        if not is_flac:
            FFMpeg.DATACODECS["flac"] = "flac"

        try:
            splitter = FFCueSplitter(
                filename=cue_file,
                outputdir=output_dir,
                outputformat="flac",
                **({"ffmpeg_add_params": "-c:a copy"} if is_flac else {}),
            )
            _open_cue(splitter, cue_file)
            tracks = splitter.audiotracks
            for track in tracks:
                if artist is not None:
                    track["PERFORMER"] = artist
                if album is not None:
                    track["ALBUM"] = album
            recipes = splitter.commandargs(tracks)
            for cmd, info in recipes["recipes"]:
                splitter.command_runner(cmd, info["duration"])
        finally:
            if not is_flac and original_codec is not None:
                FFMpeg.DATACODECS["flac"] = original_codec

        output_files = [p for p in Path(output_dir).iterdir() if p.is_file()]
        if is_flac:
            for f in output_files:
                _remux(f)
        return [str(p) for p in output_files]
