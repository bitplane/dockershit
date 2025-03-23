from pathlib import Path


class Dockerfile:
    COMMANDS = (
        "ADD",
        "COPY",
        "ENV",
        "EXPOSE",
        "LABEL",
        "USER",
        "VOLUME",
        "WORKDIR",
        "CMD",
        "ENTRYPOINT",
    )

    DEFAULT_IMAGE = "alpine:latest"

    def __init__(self, path, image=None):
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
            self.lines = []
            current = ""
            for line in raw_lines:
                if current.endswith("\\"):
                    current += "\n" + line
                    continue
                current = line
                self.lines.append(line)
            # last line is a continuation
            if current != line:
                self.lines.append(current)

        cmds = [line.split(maxsplit=1) for line in self.lines if " " in line]
        froms = [cmd[1] for cmd in cmds if cmd[0].upper() == "FROM"]
        chdirs = [cmd[1] for cmd in cmds if cmd[0].upper() == "WORKDIR"]
        self.image = froms[0] if froms else self.image
        self.workdir = chdirs[-1] if chdirs else self.workdir

    def exists(self):
        return self.path.exists()

    def set_image(self, image):
        self.image = image
        for i, line in enumerate(self.lines):
            if line.upper().startswith("FROM "):
                self.lines[i] = f"FROM {image}"
                return
        self.lines.insert(0, f"FROM {image}")

    def set_pwd(self, pwd):
        self.workdir = pwd
        self.append(f"WORKDIR {pwd}")

    def append(self, line):
        self.lines.append(line)
        self.write()

    def remove_last_command(self):
        while self.lines and not self.matters(self.lines[-1]):
            self.lines.pop()
        self.lines.pop()

        self.write()

    def write(self):
        self.path.write_text("\n".join(self.lines) + "\n")

    @staticmethod
    def matters(line):
        is_empty = not line.strip()
        is_comment = line.strip().startswith("#")
        return not is_empty and not is_comment

    @staticmethod
    def is_command(line):
        """
        Case sensitive to avoid shell mismatches
        """
        parts = line.strip().split()
        return bool(parts and parts[0] in Dockerfile.COMMANDS)
