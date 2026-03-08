import cyclopts

from musictl.commands import clean_current, delete_current, play, search, update

app = cyclopts.App(name="musictl", help="Music control utility for MPD + beets")

app.command(search.app)
app.command(play.app)
app.command(update.app)
app.command(delete_current.app, name="delete-current")
app.command(clean_current.app, name="clean-current")


def main():
    app()


if __name__ == "__main__":
    main()
