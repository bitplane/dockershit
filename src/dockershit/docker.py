import subprocess
import sys

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
        is_hidden = line.startswith(" ")
        cmd = line.lstrip()
        flat_cmd = cmd.replace("\n", " ")  # Flatten for execution

        # Handle comments
        if cmd.startswith("#"):
            if not is_hidden:
                self.dockerfile.append(cmd)
            return

        # Handle Docker commands (COPY, ADD, etc.)
        if self.dockerfile.is_command(cmd):
            if not is_hidden:
                self.dockerfile.append(cmd)

                # If it's a WORKDIR command, update the internal workdir state
                if cmd.startswith("WORKDIR "):
                    # Extract the path (everything after WORKDIR)
                    path = flat_cmd.split("WORKDIR ", 1)[1].strip()
                    self.dockerfile.set_pwd(path)
                    return

            self.build()
            return

        # Handle simple cd command (without additional operators)
        if cmd.startswith("cd ") and not any(
            op in cmd for op in ["&&", "||", ";", "|", ">"]
        ):
            new_dir = cmd[3:].strip()
            self.dockerfile.set_pwd(new_dir)
            return

        # Execute shell command
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-w",
                self.dockerfile.workdir,
                self.tag,
                self.shell,
                "-c",
                flat_cmd,
            ]
        )

        if result.returncode == 0:
            if not is_hidden:
                self.dockerfile.append("")
                self.dockerfile.append(f"RUN {cmd}")
                self.build()
        else:
            self.dockerfile.append(f"# (error) RUN {cmd}")
