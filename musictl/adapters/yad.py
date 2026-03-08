import logging
import subprocess

logger = logging.getLogger(__name__)


class YadAdapter:
    def confirm(self, title: str, text: str) -> bool:
        logger.debug("Confirm dialog: %s — %s", title, text)
        result = subprocess.run(
            ["yad", "--question", f"--title={title}", f"--text={text}", "--height=1"],
            capture_output=True,
        )
        logger.debug("Confirm result: %s", "accepted" if result.returncode == 0 else "cancelled")
        return result.returncode == 0

    def form(self, title: str, fields: list[str], values: list[str] | None = None) -> list[str] | None:
        logger.debug("Form dialog: %s, fields=%s", title, fields)
        cmd = ["yad", "--form", f"--title={title}", "--separator=|"]
        for field in fields:
            cmd.append(f"--field={field}")
        if values:
            cmd.extend(values)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.debug("Form cancelled")
            return None
        parsed = result.stdout.strip().rstrip("|").split("|")
        logger.debug("Form result: %s", parsed)
        return parsed

    def notify(self, title: str, text: str) -> None:
        subprocess.run(
            ["notify-send", title, text],
            capture_output=True,
        )
