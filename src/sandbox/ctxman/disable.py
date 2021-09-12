import builtins
import importlib
import inspect
import os
import sys
import types
from typing import Any, Callable, Set, Tuple

import werkzeug

from src import error
from src import utils


#def suspend(function: Callable[..., Any]):
#    def _(*args, **kwargs):
#        replaced = builtins.__dict__.copy()
#        for name in CallGuard.BUILTINS:
#            builtins.__dict__[name] = CallGuard.BUILTINS[name]
#        retval = function(*args, **kwargs)
#        for name in CallGuard.BUILTINS:
#            builtins.__dict__[name] = replaced[name]
#        return retval
#    return _




class CallGuard(object):

    def __init__(self, calls: Tuple[str, ...], imports: Tuple[str, ...],
                 submit_dirname: str = "") -> None:
        self.calls = calls
        self.imports = imports
        self.submit_dirname = submit_dirname
        self.builtins = builtins.__dict__.copy()

    def __enter__(self) -> "CallGuard":
        """Set all built-ins not whitelisted to None."""
        exc_names = self._get_exc_names()
#        for name, obj in builtins.__dict__.items():
#            if name == "__import__":
#                builtins.__dict__[name] = self._import_restricted
#            elif name not in self.calls and name not in exc_names:
#                builtins.__dict__[name] = CallGuard.disable_function(name)
#            elif name == "open":
#                builtins.__dict__[name] = suspend(self._open)
#            elif name not in exc_names:
##                builtins.__dict__[name] = suspend(obj)
#                builtins.__dict__[name] = self._guard(name)
                

    def __exit__(self, *args) -> bool:
        """Reset all built-ins to original values."""
        for name in self.builtins:
            builtins.__dict__[name] = self.builtins[name]

    def _get_exc_names(self) -> Set[str]:
        return {name for name, obj in builtins.__dict__.items()
                if inspect.isclass(obj) and issubclass(obj, BaseException)}

    def _guard(self, name: str) -> Callable[..., Any]:
        def _(*args, **kwargs):
            calling_module = sys._getframe(1).f_code.co_filename
            return self.builtins[name](*args, **kwargs)
        return _

    def _import_restricted(self, module_name: str, *args) -> types.ModuleType:
        """Import a module if it is whitelisted."""
        calling_module = sys._getframe(1).f_code.co_filename
        if module_name == "sys":
            # only add sys.argv to global namespace
            args[0]["sys.argv"] = importlib.import_module("sys").argv
        elif module_name in self.imports:
            module = importlib.__import__(module_name, *args)
            for name, obj in module.__dict__.items():
                if callable(obj):
                    module.__dict__[name] = suspend(obj)
            return module
        else:
            raise ImportError("Prohibited module: " + module_name)

    def _open(self, filename: str, mode: str = "r", encoding: str = "utf-8"):
        filename = werkzeug.utils.secure_filename(os.path.basename(filename))
        if mode == "r":
            path = os.path.join(utils.get_top_dirname(), "public", filename)
        elif mode == "w":
            if self.submit_dirname:
                os.makedirs(self.submit_dirname, mode=0o700, exist_ok=True)
                path = os.path.join(self.submit_dirname, filename)
            else:
                path = os.devnull
        else:
            raise error.ProhibitedFileModeException
        try:
            return self.builtins.open(path, mode=mode, encoding=encoding)
        except FileNotFoundError as e:
            e.filename = filename
            raise e
