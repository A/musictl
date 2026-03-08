import cyclopts

from musictl.adapters.beets import BeetsAdapter
from musictl.config import settings
from musictl.services.library import LibraryService

app = cyclopts.App(name="import", help="Import tracks into beets library")


@app.default
def import_tracks(*args: str) -> None:
    """Import tracks via beet import. All arguments are passed through."""
    beets = BeetsAdapter()
    service = LibraryService(beets, settings)
    service.import_tracks(*args)
