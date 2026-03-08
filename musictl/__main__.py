import cyclopts

app = cyclopts.App(name="musictl", help="Music control utility for MPD + beets")


def main():
    app()


if __name__ == "__main__":
    main()
