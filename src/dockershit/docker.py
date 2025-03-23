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

        # Add original command to history but don't save to Dockerfile if prefixed with space
        is_hidden = line.startswith(" ")
        if is_hidden:
            # Strip the space for execution but don't save to Dockerfile
            cmd = line.lstrip()
        else:
            cmd = line

        if cmd.startswith("#"):
            if not is_hidden:
                self.dockerfile.append(cmd)
            return

        if self.dockerfile.is_command(cmd):
            if not is_hidden:
                self.dockerfile.append(cmd)
            self.build()
            return

        if cmd.startswith("cd "):
            new_dir = cmd[3:].strip()

            # Handle relative paths
            if not new_dir.startswith("/"):
                old_dir = self.dockerfile.workdir
                if not new_dir.endswith("/"):
                    old_dir = old_dir + "/"

                new_dir = old_dir + new_dir

            self.dockerfile.set_pwd(new_dir)
            return

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
                cmd,
            ]
        )

        if result.returncode == 0:
            if not is_hidden:
                self.dockerfile.append("")
                self.dockerfile.append(f"RUN {cmd}")
                self.build()
        else:
            self.dockerfile.append(f"# (error) RUN {cmd}")
