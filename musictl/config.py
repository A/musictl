from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    music_dir: Path = field(default_factory=lambda: Path.home() / "Music")
    mpd_host: str = "localhost"
    mpd_port: int = 6600
    beets_db_path: Path = field(default_factory=lambda: Path.home() / ".config" / "beets" / "library.db")
    playlists_dir: Path = field(default_factory=lambda: Path.home() / "Music" / "playlists")
    audio_extensions: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {".flac", ".mp3", ".ogg", ".opus", ".m4a", ".wav", ".wma", ".aac", ".ape", ".wv"}
        )
    )


settings = Settings()
