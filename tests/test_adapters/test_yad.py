from unittest.mock import MagicMock, patch

from musictl.adapters.yad import YadAdapter


@patch("musictl.adapters.yad.subprocess.run")
class TestConfirm:
    def test_returns_true_on_accept(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        assert YadAdapter().confirm("Delete?", "Are you sure?") is True
        mock_run.assert_called_once_with(
            ["yad", "--question", "--title=Delete?", "--text=Are you sure?", "--height=1"],
            capture_output=True,
        )

    def test_returns_false_on_cancel(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)

        assert YadAdapter().confirm("Delete?", "Are you sure?") is False


@patch("musictl.adapters.yad.subprocess.run")
class TestForm:
    def test_returns_field_values(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="rock|yes|\n")

        result = YadAdapter().form("Edit", ["Folder:CBE", "Confirm:CHK"])

        assert result == ["rock", "yes"]

    def test_returns_none_on_cancel(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)

        assert YadAdapter().form("Edit", ["Folder:CBE"]) is None


@patch("musictl.adapters.yad.subprocess.run")
class TestNotify:
    def test_calls_notify_send(self, mock_run):
        YadAdapter().notify("Done", "Playlists generated")

        mock_run.assert_called_once_with(
            ["notify-send", "Done", "Playlists generated"],
            capture_output=True,
        )
