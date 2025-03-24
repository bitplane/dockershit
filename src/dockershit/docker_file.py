"""
For dealing with Dockerfiles
"""

from pathlib import Path

from . import command


class Dockerfile:
    DEFAULT_IMAGE = "alpine:latest"

    def __init__(self, path: str, image=None):
        self.path = Path(path)
        self.lines = []
        self.image = image
        self.workdir = "/"
        self.load()
        if not self.exists() or not self.image:
            self.set_image(image or Dockerfile.DEFAULT_IMAGE)
        elif image:
            self.set_image(image)

    def load(self):
        if self.path.exists():
            raw_lines = self.path.read_text().splitlines()
            self.lines = self.parse_lines(raw_lines)

        cmds = [line.split(maxsplit=1) for line in self.lines if " " in line]
        froms = [cmd[1] for cmd in cmds if cmd[0].upper() == "FROM"]
        chdirs = [cmd[1] for cmd in cmds if cmd[0].upper() == "WORKDIR"]
        self.image = froms[0] if froms else self.image
        self.workdir = chdirs[-1] if chdirs else self.workdir

    def parse_lines(self, raw_lines: list[str]) -> list[str]:
        """
        Parses multi-line commands into single lines
        """
        lines = []
        current_line = ""

        for line in raw_lines:
            if current_line and current_line.endswith("\\"):
                # Continue the previous line
                current_line = current_line + "\n" + line
            else:
                # Start a new line
                if current_line:  # Add the previous completed line
                    lines.append(current_line)
                current_line = line

        # Don't forget the last line
        if current_line:
            lines.append(current_line)

        return lines

    def exists(self) -> bool:
        """
        Returns True if the file exists
        """
        return self.path.exists()

    def set_image(self, image: str):
        """
        Sets the base image, in text. Example: "alpine:latest"
        """
        self.image = image
        for i, line in enumerate(self.lines):
            if line.upper().startswith("FROM "):
                self.lines[i] = f"FROM {image}"
                self.save()
                return
        self.lines.insert(0, f"FROM {image}")
        self.save()

    def cd(self, pwd: str):
        """
        Set the working directory for the Dockerfile
        """
        # Handle relative paths
        if not pwd.startswith("/"):
            old_dir = self.workdir
            if not pwd.endswith("/"):
                old_dir = old_dir + "/"

            pwd = old_dir + pwd

        self.workdir = pwd
        self.append(f"WORKDIR {pwd}")

    def append(self, line):
        self.lines.append(line)
        self.save()

    def remove_last_command(self, reason: str = "removed"):
        """
        Actually comment it out then reload the file
        """
        i = len(self.lines)
        while i > 0:
            i -= 1
            line = self.lines[i]
            if command.matters(line):
                self.lines[i] = f"# ({reason}) " + line
                break

        self.save()
        self.load()

    def save(self):
        """
        Write the thing to a file
        """
        self.path.write_text("\n".join(self.lines) + "\n")
