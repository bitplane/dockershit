import argparse
import atexit
import readline
import subprocess
import sys
from pathlib import Path

DOCKER_COMMANDS = (
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

EXCLUDES = ["Dockerfile", "Dockerfile.history"]


def save_if_not_blank_or_space():
    line = readline.get_line_buffer()
    if line.strip() and not line.startswith(" "):
        readline.add_history(line)


def set_history_file(name: str):
    try:
        readline.read_history_file(name)
    except FileNotFoundError:
        pass

    readline.set_auto_history(False)
    readline.set_pre_input_hook(save_if_not_blank_or_space)
    atexit.register(readline.write_history_file, name)


def parse_args():
    parser = argparse.ArgumentParser(description="docker sh --it")
    parser.add_argument(
        "from_",
        nargs="?",
        default="alpine:latest",
        metavar="from",
        help="Base image to use",
    )
    parser.add_argument(
        "--shell", default="/bin/sh", help="Shell to use inside the container"
    )
    parser.add_argument("--file", default="Dockerfile", help="Dockerfile to write to")
    parser.add_argument("--tag", default="dockershit", help="Tag for the built image")
    parser.add_argument("--debug", action="store_true", help="Show Docker build output")
    return parser.parse_args()


def load_dockerfile(path):
    if path.exists():
        return path.read_text().splitlines()
    return []


def write_dockerfile(path, lines):
    path.write_text("\n".join(lines) + "\n")


def build_image(tag, file, debug):
    result = subprocess.run(
        ["docker", "build", "-t", tag, "-f", str(file), "."], capture_output=not debug
    )
    if result.returncode != 0:
        if not debug:
            sys.stderr.write(result.stderr.decode())
        sys.exit(result.returncode)
    if debug:
        sys.stdout.write(result.stdout.decode())


def is_dockerfile_cmd(cmd):
    return any(cmd.strip().upper().startswith(dcmd) for dcmd in DOCKER_COMMANDS)


def main():
    args = parse_args()
    dockerfile_path = Path(args.file)
    lines = load_dockerfile(dockerfile_path)
    if not any(line.startswith("FROM") for line in lines):
        lines.insert(0, f"FROM {args.from_}")

    set_history_file(f"{dockerfile_path}.history")

    current_dir = "/"

    while True:
        write_dockerfile(dockerfile_path, lines)
        build_image(args.tag, dockerfile_path, args.debug)

        try:
            cmd = input("# ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not cmd:
            continue

        if cmd in ("exit", "quit"):
            break

        if is_dockerfile_cmd(cmd):
            lines.append(cmd)
            continue

        if cmd.startswith("cd "):
            new_dir = cmd[3:].strip()
            test = subprocess.run(
                ["docker", "run", "--rm", args.tag, args.shell, "-c", f"cd {new_dir}"],
                capture_output=True,
            )
            if test.returncode == 0:
                lines.append(f"WORKDIR {new_dir}")
                current_dir = new_dir
            else:
                print(f"# cd failed: {new_dir}")
            continue

        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-w",
                current_dir,
                args.tag,
                args.shell,
                "-c",
                cmd,
            ]
        )
        lines.append("")

        if cmd.startswith(" "):
            continue

        if result.returncode == 0:
            lines.append(f"RUN {cmd}")
        else:
            lines.append(f"# (error) RUN {cmd}")


if __name__ == "__main__":
    main()
