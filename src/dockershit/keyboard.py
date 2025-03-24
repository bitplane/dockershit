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
        Get input from the user, with multi-line continuation via backslash.
        """
        lines = []

        while True:
            # Determine prompt based on whether we're in a continuation
            prompt = "... " if lines else "# "

            # Get input from user
            cmd = input(prompt)

            # Check for exit commands (only if this is the first line)
            if not lines and cmd in ("exit", "quit"):
                raise KeyboardInterrupt

            # Add the current line to our collection
            lines.append(cmd)

            # If the line doesn't end with backslash, we're done
            if not cmd.endswith("\\"):
                break

        # Join all lines with newlines
        full_command = "\n    ".join(lines)

        return full_command if full_command.strip() else self.input()
