import sys
from typing import Any, Callable

from src import error
from src.sandbox import sandbox
#from src.sandbox.ctxman import disable


class SafeFunctionResult(object):

    def __init__(self, retval: Any, stdout: str,
                 exc_info: error.ExcInfo) -> None:
        self.retval = retval
        self.stdout = stdout
        self.exc_info = exc_info

    def __repr__(self) -> str:
        return (self.__class__.__name__ +
                f"({repr(self.retval)}, {repr(self.stdout)}, {self.exc_info})")

    def validate(self) -> Any:
        if self.exc_info[1]:
            raise self.exc_info[1]
        return self.retval




class Null(object):

    def __eq__(self, *args) -> bool:
        return False

    def __repr__(self) -> str:
        return "NULL"

    def __getattribute__(self, *args) -> None:
        return None




class SafeFunction(object):

    @staticmethod
    def disable(name: str = "") -> Callable[..., Any]:
        def _(*args, **kwargs):
            raise error.DisabledFunctionError(name)
        return _

    @classmethod
    def not_implemented(cls, name: str, sb: sandbox.Sandbox) -> "SafeFunction":
        def _(*args, **kwargs):
            raise NotImplementedError(name)
        return SafeFunction(_, sb)

    def __init__(self, function: Callable[..., Any],
                 sb: sandbox.Sandbox, use_disable: bool = True) -> None:
        self.name: str = f"{function.__module__}.{function.__qualname__}"
        self.function: Callable[..., Any] = function
        self.sandbox: sandbox.Sandbox = sb
        self.use_disable = use_disable

    def __call__(self, *args, **kwargs) -> Any:
        return self.capture(*args, **kwargs).validate()

    def capture(self, *args, _stdin: str = "", _timeout: int = 0,
                **kwargs) -> SafeFunctionResult:
        self.sandbox.use_disable = self.use_disable
        with self.sandbox(stdin=_stdin, timeout=_timeout) as sb:
            try:
                retval = self.function(*args, **kwargs)
                exc_info = (None, None, None)
            except:
                retval = Null()
                exc_info = sys.exc_info()
        stdout = sb.get_stdout()
        return SafeFunctionResult(retval, stdout, exc_info)

    def disable_function(self):
        self.function = SafeFunction.disable()
