from unittest.mock import MagicMock, patch

import pytest

from dockershit.keyboard import Keyboard


@pytest.fixture
def mock_readline():
    """Create a mock for readline module."""
    mock = MagicMock()
    with patch("dockershit.keyboard.readline", mock):
        yield mock


@pytest.fixture
def mock_input():
    """Create a mock for builtins.input."""
    with patch("builtins.input") as mock:
        yield mock


@pytest.fixture
def keyboard(tmp_path, mock_readline):
    """Create a Keyboard instance with mocked readline."""
    history_file = tmp_path / "history.txt"
    return Keyboard(history_file)


def test_keyboard_init_new_file(tmp_path, mock_readline):
    """Test initializing with a new history file."""
    history_file = tmp_path / "nonexistent.history"
    mock_readline.read_history_file.side_effect = FileNotFoundError

    Keyboard(history_file)

    # Check that the correct methods were called
    mock_readline.read_history_file.assert_called_once_with(history_file)
    mock_readline.set_auto_history.assert_called_once_with(True)
    # Write should be registered at exit but not called yet
    mock_readline.write_history_file.assert_not_called()


def test_keyboard_init_existing_file(tmp_path, mock_readline):
    """Test initializing with an existing history file."""
    history_file = tmp_path / "history.txt"
    history_file.write_text("history line 1\nhistory line 2\n")

    Keyboard(history_file)

    # Check that the correct methods were called
    mock_readline.read_history_file.assert_called_once_with(history_file)
    mock_readline.set_auto_history.assert_called_once_with(True)
    # Write should be registered at exit but not called yet
    mock_readline.write_history_file.assert_not_called()


def test_keyboard_input(keyboard, mock_input):
    """Test keyboard input method."""
    # Test normal input
    mock_input.return_value = "RUN apt-get update"
    assert keyboard.input() == "RUN apt-get update"

    # Test input with whitespace
    mock_input.return_value = "  WORKDIR /app  "
    assert keyboard.input() == "WORKDIR /app"

    # Test exit command
    mock_input.return_value = "exit"
    with pytest.raises(KeyboardInterrupt):
        keyboard.input()

    # Test quit command
    mock_input.return_value = "quit"
    with pytest.raises(KeyboardInterrupt):
        keyboard.input()

    # Test empty inputs followed by valid input
    mock_input.side_effect = ["", "", "ENV VAR=value"]
    assert keyboard.input() == "ENV VAR=value"


def test_input_multiline(keyboard, mock_input):
    """Test multi-line input with backslash continuation."""
    # Mock a multi-line input sequence
    mock_input.side_effect = [
        "apt-get update && \\",
        "apt-get install -y \\",
        "python3 curl git",
    ]

    result = keyboard.input()

    # Check that all three inputs were requested
    assert mock_input.call_count == 3

    # Check that prompts were correct (first line uses #, continuations use ...)
    assert mock_input.call_args_list[0].args == ("# ",)
    assert mock_input.call_args_list[1].args == ("... ",)
    assert mock_input.call_args_list[2].args == ("... ",)

    # Check that the result is the combined command with backslashes removed
    # and joined with newlines, with 4-space indentation for continuation lines
    expected = "apt-get update &&\n    apt-get install -y\n    python3 curl git"
    assert result == expected
