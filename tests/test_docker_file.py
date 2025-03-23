import pytest

from dockershit.docker_file import Dockerfile


@pytest.fixture
def tmp_dockerfile_path(tmp_path):
    """Create a temporary Dockerfile path."""
    return tmp_path / "Dockerfile"


@pytest.fixture
def empty_dockerfile(tmp_dockerfile_path):
    """Create a fresh, empty Dockerfile."""
    return Dockerfile(tmp_dockerfile_path)


@pytest.fixture
def simple_dockerfile(tmp_dockerfile_path):
    """Create a Dockerfile with just FROM."""
    df = Dockerfile(tmp_dockerfile_path, "ubuntu:latest")
    return df


@pytest.fixture
def populated_dockerfile(tmp_dockerfile_path):
    """Create a Dockerfile with common commands."""
    tmp_dockerfile_path.write_text(
        "FROM ubuntu:20.04\n" "WORKDIR /app\n" "RUN echo hello"
    )
    return Dockerfile(tmp_dockerfile_path)


@pytest.fixture
def multiline_dockerfile(tmp_dockerfile_path):
    """Create a Dockerfile with multiline commands."""
    tmp_dockerfile_path.write_text(
        "FROM ubuntu:20.04\n"
        "RUN apt-get update && \\\n"
        "    apt-get install -y python3 && \\\n"
        "    apt-get clean\n"
    )
    return Dockerfile(tmp_dockerfile_path)


@pytest.fixture
def indented_dockerfile(tmp_dockerfile_path):
    """Create a Dockerfile with indented lines."""
    tmp_dockerfile_path.write_text(
        "FROM ubuntu:20.04\n" "    WORKDIR /app\n" "\tRUN echo hello"
    )
    return Dockerfile(tmp_dockerfile_path)


def test_init_with_nonexistent_file(tmp_dockerfile_path):
    """Test initializing with a file that doesn't exist."""
    df = Dockerfile(tmp_dockerfile_path)
    assert df.image == "alpine:latest"
    assert df.workdir == "/"
    assert df.lines == ["FROM alpine:latest"]


def test_init_with_image_parameter(tmp_dockerfile_path):
    """Test initializing with image parameter."""
    df = Dockerfile(tmp_dockerfile_path, "nginx:latest")
    assert df.image == "nginx:latest"
    assert df.workdir == "/"
    assert df.lines == ["FROM nginx:latest"]


def test_init_with_existing_file(populated_dockerfile):
    """Test initializing with an existing file."""
    assert populated_dockerfile.image == "ubuntu:20.04"
    assert populated_dockerfile.workdir == "/app"
    assert populated_dockerfile.lines == [
        "FROM ubuntu:20.04",
        "WORKDIR /app",
        "RUN echo hello",
    ]


def test_init_with_indented_file(indented_dockerfile):
    """Test initializing with indented lines."""
    assert indented_dockerfile.image == "ubuntu:20.04"
    assert indented_dockerfile.workdir == "/app"
    assert indented_dockerfile.lines == [
        "FROM ubuntu:20.04",
        "    WORKDIR /app",
        "\tRUN echo hello",
    ]


def test_multiline_command_parsing(multiline_dockerfile):
    """Test parsing multiline commands with continuations."""
    assert len(multiline_dockerfile.lines) == 2
    assert multiline_dockerfile.lines[0] == "FROM ubuntu:20.04"
    assert "apt-get update" in multiline_dockerfile.lines[1]
    assert "apt-get install" in multiline_dockerfile.lines[1]
    assert "apt-get clean" in multiline_dockerfile.lines[1]


def test_set_image_existing_from(populated_dockerfile):
    """Test setting image when FROM already exists."""
    populated_dockerfile.set_image("nginx:latest")

    assert populated_dockerfile.image == "nginx:latest"
    assert populated_dockerfile.lines[0] == "FROM nginx:latest"
    assert populated_dockerfile.path.read_text().splitlines()[0] == "FROM nginx:latest"


def test_set_image_no_from(tmp_dockerfile_path):
    """Test setting image when no FROM exists."""
    tmp_dockerfile_path.write_text("WORKDIR /app\nRUN echo hello")

    df = Dockerfile(tmp_dockerfile_path)
    df.set_image("nginx:latest")

    assert df.image == "nginx:latest"
    assert df.lines[0] == "FROM nginx:latest"
    assert df.path.read_text().splitlines()[0] == "FROM nginx:latest"


def test_set_pwd(empty_dockerfile):
    """Test setting the working directory."""
    empty_dockerfile.set_pwd("/usr/src/app")

    assert empty_dockerfile.workdir == "/usr/src/app"
    assert "WORKDIR /usr/src/app" in empty_dockerfile.lines
    assert "WORKDIR /usr/src/app" in empty_dockerfile.path.read_text()


def test_append(empty_dockerfile):
    """Test appending a line."""
    empty_dockerfile.append("RUN apt-get update")

    assert "RUN apt-get update" in empty_dockerfile.lines
    assert "RUN apt-get update" in empty_dockerfile.path.read_text()


def test_remove_last_command(simple_dockerfile):
    """Test removing the last command when there's only FROM."""
    simple_dockerfile.append("RUN echo hello")
    simple_dockerfile.append("# comment")
    simple_dockerfile.append("")
    simple_dockerfile.append("RUN echo world")

    simple_dockerfile.remove_last_command()

    assert "RUN echo hello" in simple_dockerfile.lines
    assert "RUN echo world" not in simple_dockerfile.lines
    assert "RUN echo hello" in simple_dockerfile.path.read_text()
    assert "RUN echo world" not in simple_dockerfile.path.read_text()


def test_remove_last_command_with_trailing_meaningless(simple_dockerfile):
    """Test removing the last command with trailing meaningless lines."""
    simple_dockerfile.append("RUN echo hello")
    simple_dockerfile.append("# comment 1")
    simple_dockerfile.append("")
    simple_dockerfile.append("# comment 2")

    simple_dockerfile.remove_last_command()

    # All meaningless lines and the last meaningful command should be gone
    assert "FROM ubuntu:latest" in simple_dockerfile.lines
    assert "RUN echo hello" not in simple_dockerfile.lines
    assert "# comment 1" not in simple_dockerfile.lines
    assert "" not in simple_dockerfile.lines
    assert "# comment 2" not in simple_dockerfile.lines


def test_matters():
    """Test the matters method."""
    assert Dockerfile.matters("RUN echo hello") is True
    assert Dockerfile.matters("  ") is False
    assert Dockerfile.matters("# comment") is False
    assert Dockerfile.matters("") is False

    # Edge cases
    assert Dockerfile.matters(" RUN echo hello") is True  # Leading whitespace
    assert Dockerfile.matters("\t\tADD file.txt /app") is True  # Tabs
    assert Dockerfile.matters("   # comment") is False  # Leading space with comment


def test_is_command():
    """Test the is_command method."""
    assert Dockerfile.is_command("ADD file /app") is True
    assert Dockerfile.is_command("COPY . /app") is True
    assert Dockerfile.is_command("ENV VAR=value") is True
    assert Dockerfile.is_command("RUN echo hello") is False  # RUN not in COMMANDS
    assert Dockerfile.is_command("from ubuntu:20.04") is False  # case sensitivity
    assert Dockerfile.is_command("echo hello") is False

    # Leading whitespace should be properly handled
    assert Dockerfile.is_command("  COPY . /app") is True
    assert Dockerfile.is_command("\tENV VAR=value") is True


def test_init_override_existing_image(tmp_dockerfile_path):
    """Test initializing with a new image when file already exists with different image."""
    # Create a file with ubuntu:20.04
    tmp_dockerfile_path.write_text("FROM ubuntu:20.04\nWORKDIR /app")

    # Initialize with a different image
    df = Dockerfile(tmp_dockerfile_path, "python:3.9")

    # Check that the image was overridden
    assert df.image == "python:3.9"
    assert df.lines[0] == "FROM python:3.9"
    # Verify the file was actually updated
    assert tmp_dockerfile_path.read_text().splitlines()[0] == "FROM python:3.9"


def test_complex_multiline_command(tmp_dockerfile_path):
    """Test parsing complex multiline commands with multiple continuations."""
    tmp_dockerfile_path.write_text(
        """FROM ubuntu:20.04
RUN apt-get update && \\
    apt-get install -y \\
        python3 \\
        python3-pip \\
        git && \\
    apt-get clean && \\
    rm -rf /var/lib/apt/lists/*
"""
    )

    df = Dockerfile(tmp_dockerfile_path)

    # Verify correct handling of complex multiline commands
    assert len(df.lines) == 2
    assert "apt-get update" in df.lines[1]
    assert "python3" in df.lines[1]
    assert "apt-get clean" in df.lines[1]
