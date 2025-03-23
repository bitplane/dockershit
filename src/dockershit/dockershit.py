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


def set_history_file(name: str):
    try:
        readline.read_history_file(name)
    except FileNotFoundError:
        pass

    def save_history():
        try:
            readline.write_history_file(name)
        except Exception:
            pass

    atexit.register(save_history)
    readline.set_auto_history(True)


def parse_args(argv=None):
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
    return parser.parse_args(argv)


def load_dockerfile(path):
    if path.exists():
        return path.read_text().splitlines()
    return []


def write_dockerfile(path, lines):
    path.write_text("\n".join(lines) + "\n")


def build_image(tag, file, debug):
    result = subprocess.run(
        ["docker", "build", "-t", tag, "-f", str(file), "."],
        capture_output=not debug,
        text=True,
    )

    if result.returncode != 0:
        if not debug:
            sys.stderr.write(result.stderr)
        sys.exit(result.returncode)

    if debug and result.stdout:
        sys.stdout.write(result.stdout)


def is_dockerfile_cmd(cmd):
    parts = cmd.strip().split()
    if not parts:
        return False
    return parts[0] in DOCKER_COMMANDS


def run_interactive_session(
    args, input_fn=input, print_fn=print, run_fn=subprocess.run
):
    dockerfile_path = Path(args.file)
    history_path = dockerfile_path.with_suffix(dockerfile_path.suffix + ".history")

    lines = load_dockerfile(dockerfile_path)
    if not any(line.startswith("FROM") for line in lines):
        lines.insert(0, f"FROM {args.from_}")

    set_history_file(str(history_path))

    current_dir = "/"

    rebuild = True

    while True:
        write_dockerfile(dockerfile_path, lines)
        if rebuild:
            build_image(args.tag, dockerfile_path, args.debug)
            rebuild = False

        try:
            cmd = input_fn("# ")
        except (EOFError, KeyboardInterrupt):
            break

        if not cmd.strip():
            continue

        cmd = cmd.strip()

        if cmd in ("exit", "quit"):
            break

        if is_dockerfile_cmd(cmd):
            lines.append(cmd)
            continue

        result = run_fn(
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
        success = result.statuscode == 0

        if cmd.startswith("cd ") and success:
            new_dir = cmd[3:]
            lines.append(f"WORKDIR {new_dir}")
            current_dir = new_dir
            rebuild = True

        if cmd.startswith(" "):
            continue

        if success:
            lines.append(f"RUN {cmd}")
            rebuild = True
        else:
            lines.append(f"# (error) RUN {cmd}")


def main(argv=None):
    args = parse_args(argv)
    run_interactive_session(args)


if __name__ == "__main__":
    main()
