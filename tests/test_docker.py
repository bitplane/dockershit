from unittest.mock import MagicMock, patch

import pytest

from dockershit.docker import Docker
from dockershit.docker_file import Dockerfile


@pytest.fixture
def tmp_dockerfile_path(tmp_path):
    """Create a temporary Dockerfile path."""
    return tmp_path / "Dockerfile"


@pytest.fixture
def empty_dockerfile(tmp_dockerfile_path):
    """Create a fresh, empty Dockerfile."""
    df = Dockerfile(tmp_dockerfile_path, "ubuntu:latest")
    return df


@pytest.fixture
def simple_dockerfile(tmp_dockerfile_path):
    """Create a Dockerfile with just a FROM and one command."""
    df = Dockerfile(tmp_dockerfile_path, "ubuntu:latest")
    df.append("RUN echo 'Hello, World!'")
    return df


@pytest.fixture
def complex_dockerfile(tmp_dockerfile_path):
    """Create a Dockerfile with multiple commands."""
    df = Dockerfile(tmp_dockerfile_path, "python:3.9")
    df.append("WORKDIR /app")
    df.append("COPY requirements.txt .")
    df.append("RUN pip install -r requirements.txt")
    df.append("COPY . .")
    return df


@pytest.fixture
def docker_success():
    """Mock successful Docker command execution."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Build successful", stderr=""
        )
        yield mock_run


@pytest.fixture
def docker_fails():
    """Mock failed Docker command execution."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Build failed"
        )
        yield mock_run


@pytest.fixture
def docker_with_empty_dockerfile(empty_dockerfile):
    """Create a Docker instance with an empty Dockerfile."""
    return Docker(empty_dockerfile, "/bin/sh", "test-tag", debug=False)


@pytest.fixture
def docker_with_simple_dockerfile(simple_dockerfile):
    """Create a Docker instance with a simple Dockerfile."""
    return Docker(simple_dockerfile, "/bin/sh", "test-tag", debug=False)


@pytest.fixture
def docker_with_complex_dockerfile(complex_dockerfile):
    """Create a Docker instance with a complex Dockerfile."""
    return Docker(complex_dockerfile, "/bin/sh", "test-tag", debug=False)


@pytest.fixture
def docker_debug_mode(empty_dockerfile):
    """Create a Docker instance in debug mode."""
    return Docker(empty_dockerfile, "/bin/sh", "test-tag", debug=True)


def test_build_success(docker_with_empty_dockerfile, docker_success):
    """Test successful build."""
    result = docker_with_empty_dockerfile.build()

    assert result is True
    docker_success.assert_called_once()


def test_build_failure(docker_with_simple_dockerfile, docker_fails):
    """Test failed build."""
    result = docker_with_simple_dockerfile.build()

    assert result is False
    docker_fails.assert_called_once()
    # Verify the command was removed after build failure
    assert (
        "RUN echo 'Hello, World!'" not in docker_with_simple_dockerfile.dockerfile.lines
    )


def test_build_debug_mode(docker_debug_mode):
    """Test build in debug mode."""
    with patch("subprocess.run") as mock_run, patch("sys.stdout.write") as mock_stdout:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Debug output"

        result = docker_debug_mode.build()

        assert result is True
        mock_run.assert_called_once_with(
            [
                "docker",
                "build",
                "-t",
                "test-tag",
                "-f",
                str(docker_debug_mode.dockerfile.path),
                ".",
            ],
            capture_output=False,
            text=True,
        )
        mock_stdout.assert_called_once_with("Debug output")


def test_input_empty_line(docker_with_empty_dockerfile):
    """Test input with empty line."""
    initial_lines = docker_with_empty_dockerfile.dockerfile.lines.copy()
    docker_with_empty_dockerfile.input("")
    assert docker_with_empty_dockerfile.dockerfile.lines == initial_lines


def test_input_comment(docker_with_empty_dockerfile):
    """Test input with comment."""
    docker_with_empty_dockerfile.input("# This is a comment")
    assert "# This is a comment" in docker_with_empty_dockerfile.dockerfile.lines


def test_input_dockerfile_command(docker_with_empty_dockerfile):
    """Test input with Dockerfile command."""
    with patch.object(docker_with_empty_dockerfile, "build") as mock_build:
        docker_with_empty_dockerfile.input("WORKDIR /usr/src/app")

        assert "WORKDIR /usr/src/app" in docker_with_empty_dockerfile.dockerfile.lines
        mock_build.assert_called_once()


def test_input_cd_command(docker_with_empty_dockerfile):
    """Test input with cd command."""
    docker_with_empty_dockerfile.input("cd /usr/src/app")

    assert docker_with_empty_dockerfile.dockerfile.workdir == "/usr/src/app"
    assert "WORKDIR /usr/src/app" in docker_with_empty_dockerfile.dockerfile.lines


def test_input_cd_relative_path(docker_with_empty_dockerfile):
    """Test input with relative cd command."""
    docker_with_empty_dockerfile.dockerfile.workdir = "/app"

    docker_with_empty_dockerfile.input("cd src")

    assert docker_with_empty_dockerfile.dockerfile.workdir == "/app/src"
    assert "WORKDIR /app/src" in docker_with_empty_dockerfile.dockerfile.lines


def test_input_shell_command_success(docker_with_empty_dockerfile):
    """Test input with successful shell command."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        with patch.object(docker_with_empty_dockerfile, "build") as mock_build:
            docker_with_empty_dockerfile.input("apt-get update")

            mock_run.assert_called_once()
            assert "" in docker_with_empty_dockerfile.dockerfile.lines
            assert "RUN apt-get update" in docker_with_empty_dockerfile.dockerfile.lines
            mock_build.assert_called_once()


def test_input_shell_command_failure(docker_with_empty_dockerfile):
    """Test input with failed shell command."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1

        initial_line_count = len(docker_with_empty_dockerfile.dockerfile.lines)
        docker_with_empty_dockerfile.input("apt-get install nonexistent-package")

        mock_run.assert_called_once()
        assert (
            "# (error) RUN apt-get install nonexistent-package"
            in docker_with_empty_dockerfile.dockerfile.lines
        )
        # Ensure no empty line was added before the error comment
        assert (
            len(docker_with_empty_dockerfile.dockerfile.lines) == initial_line_count + 1
        )


def test_multiple_commands(docker_with_empty_dockerfile):
    """Test running multiple commands in sequence."""
    with patch("subprocess.run") as mock_run, patch.object(
        docker_with_empty_dockerfile, "build"
    ) as mock_build:
        mock_run.return_value.returncode = 0

        docker_with_empty_dockerfile.input("WORKDIR /app")
        docker_with_empty_dockerfile.input("# Install dependencies")

        with patch.object(
            docker_with_empty_dockerfile.dockerfile, "append"
        ) as mock_append:
            docker_with_empty_dockerfile.input("apt-get update")
            mock_append.assert_any_call("")
            mock_append.assert_any_call("RUN apt-get update")

        assert "WORKDIR /app" in docker_with_empty_dockerfile.dockerfile.lines
        assert "# Install dependencies" in docker_with_empty_dockerfile.dockerfile.lines
        assert mock_build.call_count >= 2
