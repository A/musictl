import sys
from pathlib import Path

import cyclopts

from musictl.adapters.beets import BeetsAdapter
from musictl.config import settings

app = cyclopts.App(name="search", help="Search tracks in beets library")


@app.default
def search(query: str) -> None:
    """Search for tracks and print their paths (one per line)."""
    beets = BeetsAdapter()
    results = beets.query(query)
    if not results:
        sys.exit(1)
    for track in results:
        path = track.get("path", "")
        if path:
            try:
                print(Path(path).relative_to(settings.music_dir))
            except ValueError:
                print(path)
