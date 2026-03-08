import cyclopts

from musictl.commands import play, random, search

app = cyclopts.App(name="musictl", help="Music control utility for MPD + beets")

app.command(search.app)
app.command(play.app)
app.command(random.app)


def main():
    app()


if __name__ == "__main__":
    main()
