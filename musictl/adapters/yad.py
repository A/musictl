import subprocess


class YadAdapter:
    def confirm(self, title: str, text: str) -> bool:
        result = subprocess.run(
            ["yad", "--question", f"--title={title}", f"--text={text}"],
            capture_output=True,
        )
        return result.returncode == 0

    def form(self, title: str, fields: list) -> list[str] | None:
        cmd = ["yad", "--form", f"--title={title}", "--separator=|"]
        for field in fields:
            cmd.append(f"--field={field}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None
        return result.stdout.strip().rstrip("|").split("|")

    def notify(self, title: str, text: str) -> None:
        subprocess.run(
            ["notify-send", title, text],
            capture_output=True,
        )
