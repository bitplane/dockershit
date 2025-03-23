import tempfile
from pathlib import Path

import pytest

from dockershit.dockershit import (
    DOCKER_COMMANDS,
    is_dockerfile_cmd,
    load_dockerfile,
    write_dockerfile,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def dockerfile_path(temp_dir):
    return temp_dir / "Dockerfile"


def test_load_dockerfile_empty(dockerfile_path):
    """Test loading from a non-existent file returns empty list"""
    lines = load_dockerfile(dockerfile_path)
    assert lines == []


def test_load_dockerfile_existing(dockerfile_path):
    """Test loading from an existing file returns content as lines"""
    content = "FROM alpine:latest\nRUN echo hello"
    dockerfile_path.write_text(content)

    lines = load_dockerfile(dockerfile_path)
    assert lines == ["FROM alpine:latest", "RUN echo hello"]


def test_write_dockerfile(dockerfile_path):
    """Test writing lines to a Dockerfile"""
    lines = ["FROM alpine:latest", "RUN echo hello"]
    write_dockerfile(dockerfile_path, lines)

    assert dockerfile_path.exists()
    assert dockerfile_path.read_text() == "FROM alpine:latest\nRUN echo hello\n"


def test_is_dockerfile_cmd():
    """Test detection of Dockerfile commands"""
    # Valid Dockerfile commands
    for cmd in DOCKER_COMMANDS:
        assert is_dockerfile_cmd(f"{cmd} something")
        assert is_dockerfile_cmd(f"{cmd.lower()} something")
        assert is_dockerfile_cmd(f"  {cmd} something")

    # Not Dockerfile commands
    assert not is_dockerfile_cmd("echo hello")
    assert not is_dockerfile_cmd("apt-get install -y python")
