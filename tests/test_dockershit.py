from unittest.mock import MagicMock, patch

import pytest

from dockershit.dockershit import main, parse_args, run


def test_parse_args_defaults():
    """Test parsing arguments with defaults."""
    args = parse_args([])

    assert args.image is None
    assert args.shell == "/bin/sh"
    assert args.file == "Dockerfile"
    assert args.tag == "dockershit"
    assert args.debug is False


def test_parse_args_custom():
    """Test parsing arguments with custom values."""
    args = parse_args(
        [
            "python:3.9",
            "--shell",
            "/bin/bash",
            "--file",
            "custom.Dockerfile",
            "--tag",
            "myapp",
            "--debug",
        ]
    )

    assert args.image == "python:3.9"
    assert args.shell == "/bin/bash"
    assert args.file == "custom.Dockerfile"
    assert args.tag == "myapp"
    assert args.debug is True


@pytest.fixture
def mock_dockerfile():
    """Mock Dockerfile class."""
    with patch("dockershit.dockershit.Dockerfile") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock, mock_instance


@pytest.fixture
def mock_docker():
    """Mock Docker class."""
    with patch("dockershit.dockershit.Docker") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock, mock_instance


@pytest.fixture
def mock_keyboard():
    """Mock Keyboard class."""
    with patch("dockershit.dockershit.Keyboard") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock, mock_instance


def test_run(mock_dockerfile, mock_docker, mock_keyboard):
    """Test the run function."""
    dockerfile_mock, dockerfile_instance = mock_dockerfile
    docker_mock, docker_instance = mock_docker
    keyboard_mock, keyboard_instance = mock_keyboard

    # Set up the keyboard input to exit after one command
    keyboard_instance.input.side_effect = ["RUN echo hello", KeyboardInterrupt]

    # Run the function
    run("Dockerfile", "python:3.9", "/bin/sh", "myapp", False)

    # Check that the classes were initialized correctly
    dockerfile_mock.assert_called_once_with("Dockerfile", image="python:3.9")
    docker_mock.assert_called_once_with(
        dockerfile_instance, "/bin/sh", "myapp", debug=False
    )

    # Check that Docker's build method was called
    docker_instance.build.assert_called_once()

    # Check that the keyboard's input method was used
    keyboard_instance.input.assert_called()

    # Check that the docker's input method was called with the keyboard input
    docker_instance.input.assert_called_with("RUN echo hello")


def test_main():
    """Test the main function."""
    with patch("dockershit.dockershit.parse_args") as mock_parse_args, patch(
        "dockershit.dockershit.run"
    ) as mock_run:

        # Set up the mock return value
        mock_args = MagicMock()
        mock_args.image = "python:3.9"
        mock_args.shell = "/bin/bash"
        mock_args.file = "custom.Dockerfile"
        mock_args.tag = "myapp"
        mock_args.debug = True
        mock_parse_args.return_value = mock_args

        # Call main
        main(["python:3.9", "--debug"])

        # Check that parse_args was called with the correct arguments
        mock_parse_args.assert_called_once_with(["python:3.9", "--debug"])

        # Check that run was called with the correct arguments
        mock_run.assert_called_once_with(
            path="custom.Dockerfile",
            image="python:3.9",
            shell="/bin/bash",
            tag="myapp",
            debug=True,
        )
