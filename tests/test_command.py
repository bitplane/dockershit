from dockershit.command import is_dockerfile, matters


def test_matters():
    """Test the matters method."""
    assert matters("RUN echo hello") is True
    assert matters("  ") is False
    assert matters("# comment") is False
    assert matters("") is False

    # Edge cases
    assert matters(" RUN echo hello") is True  # Leading whitespace
    assert matters("\t\tADD file.txt /app") is True  # Tabs
    assert matters("   # comment") is False  # Leading space with comment


def test_is_dockerfile():
    """Test the is_command method."""
    assert is_dockerfile("ADD file /app") is True
    assert is_dockerfile("COPY . /app") is True
    assert is_dockerfile("ENV VAR=value") is True
    assert is_dockerfile("RUN echo hello") is False  # RUN not in COMMANDS
    assert is_dockerfile("from ubuntu:20.04") is False  # case sensitivity
    assert is_dockerfile("echo hello") is False

    # Leading whitespace should be properly handled
    assert is_dockerfile("  COPY . /app") is True
    assert is_dockerfile("\tENV VAR=value") is True
