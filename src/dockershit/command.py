"""
Helpers for dealing with commands
"""

DOCKERFILE_COMMANDS = (
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

FANCY_TOKENS = ("|", "&", "(", ")", "<", ">", ";", "[", "]", "{", "}", "$")


def split_command(line: str) -> str:
    """
    Get the command and args from a line
    """
    line = line.strip()
    split = line.split(maxsplit=1)
    return split + [""] * (len(split) - 2)


def is_dockerfile(line: str) -> bool:
    """
    Case sensitive to avoid shell mismatches
    """
    name, _ = split_command(line)
    return bool(name and name in DOCKERFILE_COMMANDS)


def is_simple(line: str) -> bool:
    """
    Just a command with params; no operators, subshells, pipes,
    redirects or any of that fancy stuff.
    """
    return not any(token in line for token in FANCY_TOKENS)


def is_hidden(line: str) -> bool:
    """
    If this line should be hidden
    """
    return line.startswith(" ")


def matters(line: str) -> bool:
    """
    Does this line even do anything?
    """
    is_empty = not line.strip()
    is_comment = line.strip().startswith("#")
    return not is_empty and not is_comment


def flatten(lines: str) -> str:
    """
    Flatten a multi-line command into a single line
    """
    return lines.replace("\n", " ")
