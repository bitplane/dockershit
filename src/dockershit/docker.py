import subprocess
import sys

from . import command
from .docker_file import Dockerfile


class Docker:
    def __init__(self, dockerfile: Dockerfile, shell, tag, debug=False):
        self.dockerfile = dockerfile
        self.shell = shell
        self.tag = tag
        self.debug = debug

    def build(self):
        result = subprocess.run(
            ["docker", "build", "-t", self.tag, "-f", str(self.dockerfile.path), "."],
            capture_output=not self.debug,
            text=True,
        )

        if result.returncode != 0:
            if not self.debug:
                sys.stderr.write(result.stderr)
            self.dockerfile.remove_last_command()
            return False

        if self.debug and result.stdout:
            sys.stdout.write(result.stdout)

        return True

    def input(self, line):
        if not line:
            return

        # Check if command should be hidden (starts with space)
        is_hidden = command.is_hidden(line)
        cmd = line.lstrip()
        flat_cmd = command.flatten(line)

        # Handle comments
        if cmd.startswith("#"):
            if not is_hidden:
                self.dockerfile.append(cmd)
            return

        # Handle Docker commands (COPY, ADD, etc.)
        if command.is_dockerfile(cmd):
            if not is_hidden:
                self.dockerfile.append(cmd)

                # If it's a WORKDIR command, update the internal workdir state
                if cmd.startswith("WORKDIR "):
                    # Extract the path (everything after WORKDIR)
                    path = flat_cmd.split("WORKDIR ", 1)[1].strip()
                    self.dockerfile.cd(path)
                    return

            self.build()
            return

        # Handle simple cd command (without additional operators)
        if cmd.startswith("cd ") and not self.is_multi_command(cmd):
            new_dir = cmd[3:].strip()
            self.dockerfile.cd(new_dir)
            return

        result = self.run(cmd)

        if result.returncode == 0:
            if not is_hidden:
                self.dockerfile.append("")
                self.dockerfile.append(f"RUN {cmd}")
                self.build()
        else:
            self.dockerfile.append(f"# (error) RUN {cmd}")

    def run(self, cmd):
        """
        Run a command in the Docker container
        """
        return subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-w",
                self.dockerfile.workdir,
                self.tag,
                self.shell,
                "-c",
                cmd,
            ]
        )

    @staticmethod
    def is_multi_command(cmd):
        """
        Check if the command is a special command
        """
        return any(token in cmd for token in ["&&", "||", ";", "|", ">", "<"])
