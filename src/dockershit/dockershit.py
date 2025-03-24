#!/usr/bin/env python3
import argparse
import sys

from .docker import Docker
from .docker_file import Dockerfile
from .keyboard import Keyboard


def parse_args(argv: list[str] = sys.argv[1:]):
    """
    Nobody likes an argument, but sometimes you just have to parse them.
    """
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


def run(path: str, image: str, shell: str, tag: str, debug: bool):
    """
    The input loop.
    """
    dockerfile = Dockerfile(path, image=image)
    docker = Docker(dockerfile, shell, tag, debug=debug)  # Pass debug here
    docker.build()  # No arguments here
    keyboard = Keyboard(
        str(dockerfile.path.with_suffix(dockerfile.path.suffix + ".history"))
    )

    while True:
        try:
            cmd = keyboard.input()
        except EOFError:  # for electric rocks
            break
        except KeyboardInterrupt:  # for bags of water
            break

        docker.input(cmd)


def main(argv: str = sys.argv[1:]):
    """
    The main course.
    """
    args = parse_args(argv)
    run(
        path=args.file,
        image=args.image,
        shell=args.shell,
        tag=args.tag,
        debug=args.debug,
    )


# we should look at these and weep
if __name__ == "__main__":
    main()
