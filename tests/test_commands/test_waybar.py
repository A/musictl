import json

from musictl.commands.waybar import _build_output


class FakeService:
    def __init__(self, track: dict[str, str] | None) -> None:
        self._track = track

    def current_track(self) -> dict[str, str] | None:
        return self._track


def _output(track: dict[str, str] | None) -> dict[str, str]:
    return json.loads(_build_output(FakeService(track)))  # pyright: ignore[reportArgumentType]


class TestBuildOutput:
    def test_escapes_pango_markup_specials(self) -> None:
        # Waybar parses text/tooltip as Pango markup; raw &, <, > render blank.
        out = _output(
            {"folder": "Ambient", "playlists": "Soundtrack", "artist": "Kavinsky & Lovefoxxx", "title": "Wrong Floor"},
        )

        assert "&amp;" in out["text"]
        assert "Kavinsky & Lovefoxxx" not in out["text"]
        assert out["tooltip"] == " Kavinsky &amp; Lovefoxxx - Wrong Floor"

    def test_escapes_angle_brackets(self) -> None:
        out = _output({"folder": "", "playlists": "", "artist": "<x>", "title": "<y>"})

        assert "&lt;x&gt;" in out["text"]
        assert "<" not in out["text"]

    def test_plain_track_unchanged(self) -> None:
        out = _output({"folder": "Ambient", "playlists": "Soundtrack", "artist": "Yoshimi", "title": "Gelmir"})

        assert "Ambient" in out["text"]
        assert "Yoshimi" in out["text"]

    def test_no_track_is_stopped(self) -> None:
        out = _output(None)

        assert out["text"] == ""
        assert out["class"] == "stopped"
