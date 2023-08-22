import sys
from typing import Any, Tuple, Union

from src import error
from src.sandbox.ctxman import disable
from src.sandbox.ctxman import suppress
from src.sandbox.ctxman import timer


ContextManager = Union[disable.CallGuard, #disable.ImportGuard,
                       suppress.Suppressor, timer.Timer]


class Sandbox(object):
    """Context manager for safely handling a module."""

    def __init__(self, calls: Tuple[str, ...], imports: Tuple[str, ...],
                 dirname: str, keep_prompt: bool) -> None:
        self.ctxmans = (disable.CallGuard(calls, imports, dirname),
                        suppress.Suppressor(keep_prompt=keep_prompt),
                        timer.Timer(dirname))
        self.use_disable: bool = True
        self._reclimit = sys.getrecursionlimit()
        self._depth: int = 0

    def __enter__(self) -> "Sandbox":
        if self._depth == 0:
            sys.setrecursionlimit(self._reclimit // 2)
            for cm in self.ctxmans:
                if self.use_disable or not cm.__module__.endswith(".disable"):
                    cm.__enter__()
        self._depth += 1
        return self

    def __exit__(self, *args) -> bool:
        self._depth -= 1
        if self._depth == 0:
            sys.setrecursionlimit(self._reclimit)
            for cm in self.ctxmans[::-1]:
                cm.__exit__()
        self.use_disable = True
        return True

    def __call__(self, stdin: str = "", timeout: int = 0) -> "Sandbox":
        if stdin:
            try:
                self.get_ctxman("Suppressor").set_stdin(stdin)
            except error.CaseyRuntimeError:
                pass
        if timeout:
            try:
                self.get_ctxman("Timer").set_timeout(timeout)
            except error.CaseyRuntimeError:
                pass
        return self

    def get_ctxman(self, name: str) -> ContextManager:
        """
        Retrieve and return a context manager with the given name from the
        Sandbox's list of context managers. If not found, raise an error.
        """
        for cm in self.ctxmans:
            if cm.__class__.__name__ == name:
                return cm
        raise error.CaseyRuntimeError("Context manager not found: " + name)

    def call_builtin(self, name: str, *args) -> Any:
        return self.get_ctxman("CallGuard").BUILTINS[name](*args)

    def get_stdout(self) -> str:
        """
        Return the contents of stdout, as accumulated by the Suppressor context
        manager.
        """
        try:
            return self.get_ctxman("Suppressor").stdout
        except error.CaseyRuntimeError:
            return ""

    def has_expired(self) -> bool:
        """
        Return True if the Timer context manager fired an alarm and False
        otherwise.
        """
        return self.get_ctxman("Timer").has_expired

#    def load_module(self, name: str, source: str) -> types.ModuleType:
#        """
#        Dynamically load a module with the given name and source code.
#
#        Important: To load the module securely, this method should only be
#        called within the Sandbox context manager.
#
#            with Sandbox(...) as sb:
#                module = sb.load_module(...)
#        """
#        spec = importlib.util.spec_from_loader(name, loader=None)
#        module = importlib.util.module_from_spec(spec)
#        self.call("exec", source, module.__dict__)
#        return module
