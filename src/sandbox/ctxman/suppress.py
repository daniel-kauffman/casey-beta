import builtins
import io
import sys

from src import error


class Suppressor(object):
    """Context manager for input and output streams."""

    def __init__(self, keep_prompt: bool = False, stdin: str = "",
                 capture_stderr: bool = False) -> None:
        self.lines = stdin.splitlines(True)
        self.keep_prompt = keep_prompt
        self.input = builtins.input
        self.stdout = ""
        self.refout = sys.stdout
        self.stderr = ""
        self.referr = sys.stderr if capture_stderr else None

    def set_stdin(self, stdin: str) -> None:
        self.lines = stdin.splitlines(True)

    def _promptless_input(self, prompt: str = ""):
        if not self.keep_prompt:
            prompt = ""
        refin = sys.stdin
        try:
            line = self.lines.pop(0)
            with io.StringIO(line) as sys.stdin:
                return self.input(prompt)
        except IndexError:
            raise error.CaseyInputError("No Input Available")
        finally:
            sys.stdin = refin

    def __enter__(self):
        builtins.input = self._promptless_input
        sys.stdout = io.StringIO()
        if self.referr:
            sys.stderr = io.StringIO()
        return self

    def __exit__(self, *args) -> bool:
        builtins.input = self.input
        self.stdout = sys.stdout.getvalue()
        sys.stdout.close()
        sys.stdout = self.refout
        if self.referr:
            self.stderr = sys.stderr.getvalue()
            sys.stderr.close()
            sys.stderr = self.referr
        if self.stdout.strip():
            print(self.stdout)
        if self.stderr.strip():
            print(self.stderr)
        return True

    def print_to_stderr(self) -> None:
        print(type(sys.stdout), file=sys.stderr, flush=True)
