import cyclopts

from musictl.commands import (
    clean_current,
    cue_split,
    delete_current,
    generate_playlists,
    import_tracks,
    play,
    search,
    update,
)

app = cyclopts.App(name="musictl", help="Music control utility for MPD + beets")

app.command(search.app)
app.command(play.app)
app.command(update.app)
app.command(delete_current.app, name="delete-current")
app.command(clean_current.app, name="clean-current")
app.command(import_tracks.app, name="import")
app.command(cue_split.app, name="cue-split")
app.command(generate_playlists.app, name="generate-playlists")


def main():
    app()


if __name__ == "__main__":
    main()
