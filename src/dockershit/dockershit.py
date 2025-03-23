import argparse
import sys

from .docker import Docker
from .docker_file import Dockerfile
from .keyboard import Keyboard


def parse_args(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description="docker sh --it")
    parser.add_argument(
        "image", nargs="?", default=None, metavar="image", help="Base image to use"
    )
    parser.add_argument(
        "--shell", default="/bin/sh", help="Shell to use inside the container"
    )
    parser.add_argument("--file", default="Dockerfile", help="Dockerfile to write to")
    parser.add_argument("--tag", default="dockershit", help="Tag for the built image")
    parser.add_argument("--debug", action="store_true", help="Show Docker build output")
    return parser.parse_args(argv)


def run(path, image, shell, tag, debug):
    dockerfile = Dockerfile(path, image=image)
    docker = Docker(dockerfile, shell, tag, debug=debug)  # Pass debug here
    docker.build()  # No arguments here
    keyboard = Keyboard(
        str(dockerfile.path.with_suffix(dockerfile.path.suffix + ".history"))
    )

    while True:
        try:
            cmd = keyboard.input()
        except KeyboardInterrupt:
            break

        docker.input(cmd)


def main(argv=sys.argv[1:]):
    args = parse_args(argv)
    run(
        path=args.file,
        image=args.image,
        shell=args.shell,
        tag=args.tag,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
