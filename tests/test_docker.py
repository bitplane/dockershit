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
def docker_safe():
    with patch("subprocess.run") as mock_run:
        yield mock_run


@pytest.fixture
def docker_mock():
    with patch("dockershit.docker.Docker.is_top_layer_empty") as mock_empty:
        mock_empty.return_value = False
        yield mock_empty


@pytest.fixture
def docker_success(docker_mock):
    """Mock successful Docker command execution."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Build successful", stderr=""
        )
        yield mock_run


@pytest.fixture
def docker_fails(docker_mock):
    """Mock failed Docker command execution."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Build failed"
        )
        yield mock_run


@pytest.fixture
def docker_with_no_file(empty_dockerfile, docker_mock):
    """Create a Docker instance with an empty Dockerfile."""
    return Docker(empty_dockerfile, "/bin/sh", "test-tag", debug=False)


@pytest.fixture
def docker_with_simple_dockerfile(simple_dockerfile, docker_mock):
    """Create a Docker instance with a simple Dockerfile."""
    return Docker(simple_dockerfile, "/bin/sh", "test-tag", debug=False)


@pytest.fixture
def docker_with_complex_dockerfile(complex_dockerfile, docker_mock):
    """Create a Docker instance with a complex Dockerfile."""
    return Docker(complex_dockerfile, "/bin/sh", "test-tag", debug=False)


@pytest.fixture
def docker_debug_mode(empty_dockerfile, docker_mock):
    """Create a Docker instance in debug mode."""
    return Docker(empty_dockerfile, "/bin/sh", "test-tag", debug=True)


def test_build_success(docker_with_no_file, docker_success):
    """Test successful build."""
    result = docker_with_no_file.build()

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


def test_input_empty_line(docker_with_no_file):
    """Test input with empty line."""
    initial_lines = docker_with_no_file.dockerfile.lines.copy()
    docker_with_no_file.input("")
    assert docker_with_no_file.dockerfile.lines == initial_lines


def test_input_comment(docker_with_no_file):
    """Test input with comment."""
    docker_with_no_file.input("# This is a comment")
    assert "# This is a comment" in docker_with_no_file.dockerfile.lines


def test_input_dockerfile_command(docker_with_no_file):
    """Test input with Dockerfile command."""
    with patch.object(docker_with_no_file, "build") as mock_build:
        docker_with_no_file.input("ADD /usr/src/app")

        assert "ADD /usr/src/app" in docker_with_no_file.dockerfile.lines
        mock_build.assert_called_once()


def test_input_cd_command(docker_with_no_file):
    """Test input with cd command."""
    docker_with_no_file.input("cd /usr/src/app")

    assert docker_with_no_file.dockerfile.workdir == "/usr/src/app"
    assert "WORKDIR /usr/src/app" in docker_with_no_file.dockerfile.lines


def test_input_cd_relative_path(docker_with_no_file):
    """Test input with relative cd command."""
    docker_with_no_file.dockerfile.workdir = "/app"

    docker_with_no_file.input("cd src")

    assert docker_with_no_file.dockerfile.workdir == "/app/src"
    assert "WORKDIR /app/src" in docker_with_no_file.dockerfile.lines


def test_input_shell_command_success(docker_with_no_file):
    """Test input with successful shell command."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        with patch.object(docker_with_no_file, "build") as mock_build:
            docker_with_no_file.input("apt-get update")

            mock_run.assert_called_once()
            assert "" in docker_with_no_file.dockerfile.lines
            assert "RUN apt-get update" in docker_with_no_file.dockerfile.lines
            mock_build.assert_called_once()


def test_input_shell_command_failure(docker_with_no_file):
    """Test input with failed shell command."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1

        initial_line_count = len(docker_with_no_file.dockerfile.lines)
        docker_with_no_file.input("apt-get install nonexistent-package")

        mock_run.assert_called_once()
        assert (
            "# (error) RUN apt-get install nonexistent-package"
            in docker_with_no_file.dockerfile.lines
        )
        # Ensure no empty line was added before the error comment
        assert len(docker_with_no_file.dockerfile.lines) == initial_line_count + 1


def test_multiple_commands(docker_with_no_file):
    """Test running multiple commands in sequence."""
    with patch("subprocess.run") as mock_run, patch.object(
        docker_with_no_file, "build"
    ) as mock_build:
        mock_run.return_value.returncode = 0

        docker_with_no_file.input("WORKDIR /app")
        docker_with_no_file.input("# Install dependencies")
        docker_with_no_file.input("ADD requirements.txt /app/requirements.txt")

        with patch.object(docker_with_no_file.dockerfile, "append") as mock_append:
            docker_with_no_file.input("apt-get update")
            mock_append.assert_any_call("")
            mock_append.assert_any_call("RUN apt-get update")

        assert "WORKDIR /app" in docker_with_no_file.dockerfile.lines
        assert "# Install dependencies" in docker_with_no_file.dockerfile.lines
        assert mock_build.call_count == 2


def test_input_hidden_command(docker_with_no_file):
    """Test input with a space-prefixed command (should run but not be saved to Dockerfile)."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        initial_lines = docker_with_no_file.dockerfile.lines.copy()
        docker_with_no_file.input(" apt-get update")

        mock_run.assert_called_once()
        assert docker_with_no_file.dockerfile.lines == initial_lines
        assert "RUN apt-get update" not in docker_with_no_file.dockerfile.lines


def test_input_hidden_comment(docker_with_no_file):
    """Test input with a space-prefixed comment (should be ignored, not added to Dockerfile)."""
    initial_lines = docker_with_no_file.dockerfile.lines.copy()

    # Pass a space-prefixed comment
    docker_with_no_file.input(" # this is for the viewers at home")

    # The comment should not be added to the Dockerfile
    assert docker_with_no_file.dockerfile.lines == initial_lines
    assert (
        "# this is for the viewers at home" not in docker_with_no_file.dockerfile.lines
    )


def test_input_cd_with_operators(docker_with_no_file):
    """Test input with cd command containing additional shell operators."""
    # Initial state
    docker_with_no_file.dockerfile.workdir = "/app"

    # Test cd with &&
    docker_with_no_file.input("cd /usr/src && ls")

    # This should fail - the workdir should NOT change to "/usr/src"
    # because the cd with && should be treated as a shell command
    assert docker_with_no_file.dockerfile.workdir == "/app"
    assert "WORKDIR /usr/src" not in docker_with_no_file.dockerfile.lines[-1]
    assert "RUN cd /usr/src && ls" in docker_with_no_file.dockerfile.lines


def test_input_manual_workdir(docker_with_no_file):
    """Test input with manually entered WORKDIR command."""

    # Enter a WORKDIR instruction
    docker_with_no_file.input("WORKDIR /custom/path")

    # The workdir should be updated and the command added to Dockerfile
    assert docker_with_no_file.dockerfile.workdir == "/custom/path"
    assert "WORKDIR /custom/path" in docker_with_no_file.dockerfile.lines
