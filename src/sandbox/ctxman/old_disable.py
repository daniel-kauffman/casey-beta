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


def suspend(function: Callable[..., Any]):
    def _(*args, **kwargs):
        replaced = builtins.__dict__.copy()
        for name in CallGuard.BUILTINS:
            builtins.__dict__[name] = CallGuard.BUILTINS[name]
        retval = function(*args, **kwargs)
        for name in CallGuard.BUILTINS:
            builtins.__dict__[name] = replaced[name]
        return retval
    return _




class CallGuard(object):

    BUILTINS = builtins.__dict__.copy()

    @staticmethod
    def disable_function(name: str = "") -> Callable[..., Any]:
        def _(*args, **kwargs):
            raise error.DisabledFunctionError(name)
        return _

    def __init__(self, allowed: Tuple[str], submit_dirname: str = "") -> None:
#        self.builtins = builtins.__dict__.copy()
        self.allowed = self._add_required_builtins(allowed)
        self.submit_dirname = submit_dirname

    def __enter__(self) -> "CallGuard":
        """Set all built-ins not whitelisted to None."""
        for name in builtins.__dict__:
#            if name not in self.builtins:
            if name not in self.allowed:
                builtins.__dict__[name] = CallGuard.disable_function(name)
            elif name == "open":
                builtins.__dict__[name] = self._open

    def __exit__(self, *args) -> bool:
        """Reset all built-ins to original values."""
        for name in CallGuard.BUILTINS:
            builtins.__dict__[name] = CallGuard.BUILTINS[name]

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
            return CallGuard.BUILTINS.open(path, mode=mode, encoding=encoding)
        except FileNotFoundError as e:
            e.filename = filename
            raise e

    def _add_required_builtins(self, allowed: Tuple[str]):
        required = {"all", "bytes", "bytearray", "getattr", "hasattr", "id",
                    "isinstance", "issubclass", "map", "next", "repr", "set",
                    "str", "super", "type", "zip"}
        return tuple(set(allowed) | required | self._get_exc_names())

    def _get_exc_names(self) -> Set[str]:
        return {name for name, obj in builtins.__dict__.items()
                if inspect.isclass(obj) and issubclass(obj, BaseException)}




class ImportGuard(object):

    def __init__(self, allowed: Tuple[str]) -> None:
        self.__import__ = builtins.__import__
        self.allowed: Tuple[str] = self._add_required_modules(allowed)

    def __enter__(self):
        """Set the built-in __import__ function to _import_restricted."""
        builtins.__import__ = self._import_restricted

    def __exit__(self, *args):
        """Reset the built-in __import__ function to original."""
        builtins.__import__ = self.__import__

    def _add_required_modules(self, allowed: Tuple[str]) -> Tuple[str]:
#        allowed += ("unicodedata",)
        required = {"queue": ["collections", "heapq", "threading"]}
        return allowed + tuple(req for module in allowed
                               for req in required.get(module, []))

    def _import_restricted(self, module_name: str, *args) -> types.ModuleType:
        """Import a module if it is whitelisted."""
        if module_name == "sys":
            # only add sys.argv to global namespace
            args[0]["sys.argv"] = importlib.import_module("sys").argv
        elif module_name in self.allowed:
            return importlib.__import__(module_name, *args)
        else:
            raise ImportError("Prohibited module: " + module_name)
