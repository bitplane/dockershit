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
        while True:
            cmd = input("# ").strip()
            if not cmd:
                continue
            if cmd in ("exit", "quit"):
                raise KeyboardInterrupt
            return cmd
