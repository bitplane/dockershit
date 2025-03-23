import atexit
import readline


class Keyboard:
    def __init__(self, history_file):
        self.path = history_file
        self._setup()

    def _setup(self):
        try:
            readline.read_history_file(self.path)
        except FileNotFoundError:
            pass
        atexit.register(lambda: readline.write_history_file(self.path))
        readline.set_auto_history(True)

    def input(self):
        """
        Get input from the user, supporting multi-line input with backslash continuation.
        """
        lines = []

        while True:
            # Determine prompt based on whether we're in a continuation
            prompt = "... " if lines else "# "

            # Get input from user
            cmd = input(prompt).rstrip()

            # Check for exit commands (only if this is the first line)
            if not lines and cmd in ("exit", "quit"):
                raise KeyboardInterrupt

            # Add the current line to our collection
            lines.append(cmd)

            # If the line doesn't end with backslash, we're done
            if not cmd.endswith("\\"):
                break

            # Otherwise, remove the backslash for the next iteration
            lines[-1] = lines[-1][:-1]

        # Process the lines to add proper indentation for continuation lines
        processed_lines = [lines[0]]  # First line has no indentation

        # Add 4 space indentation to continuation lines (if there are any)
        for i in range(1, len(lines)):
            processed_lines.append("    " + lines[i])

        # Join all lines with newlines to match real Dockerfile format
        full_command = "\n".join(processed_lines).strip()

        return full_command if full_command else self.input()
