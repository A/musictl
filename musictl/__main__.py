from typing import Annotated

import cyclopts
from cyclopts import Group, Parameter

from musictl.commands import (
    clean_current,
    cue_split,
    delete_current,
    generate_playlists,
    import_tracks,
    play,
    rename_folder,
    rename_playlist,
    search,
    update,
    waybar,
)
from musictl.log import setup_logging

app = cyclopts.App(name="musictl", help="Music control utility for MPD + beets")
app.meta.group_parameters = Group("Global Options", sort_key=0)

app.command(search.app)
app.command(play.app)
app.command(update.app)
app.command(delete_current.app, name="delete-current")
app.command(clean_current.app, name="clean-current")
app.command(import_tracks.app, name="import")
app.command(cue_split.app, name="cue-split")
app.command(generate_playlists.app, name="generate-playlists")
app.command(rename_playlist.app, name="rename-playlist")
app.command(rename_folder.app, name="rename-folder")
app.command(waybar.app)


@app.meta.default
def launcher(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    verbose: Annotated[int, Parameter(name=["-v", "--verbose"], show_default=False)] = 0,
) -> None:
    """Global options.

    Parameters
    ----------
    verbose: int
        Increase output verbosity (-v info, -vv debug, -vvv trace).
    """
    setup_logging(verbose)
    app(tokens)


def main():
    app.meta()


if __name__ == "__main__":
    main()
