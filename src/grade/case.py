#import difflib
import random
#import re
#import textwrap
import traceback
from typing import Any, Callable, Sequence, Tuple

from src import error
from src.sandbox import safedef


class Case(object):

    def __init__(self, f: safedef.SafeFunction, args: Sequence[Any],
                 expect: Any, w: float = 1.0, i: str = "", o: str = "",
                 s: int = 0, t: int = 1, h: bool = True,
                 e: error.ExcInfo = (None, None, None), **kwargs) -> None:
        self.call: Callable[..., Any] = \
            lambda: f.capture(*args, _stdin=i, _timeout=t, **kwargs)
        self.seed: int = s
        self.expect: Tuple[Any, str] = (expect, o)
        self.weight: float = w
        self.passed: bool = False
        self.hidden: bool = h
        self.exc_info = e
        self.header: str = self._init_header(f, args, s, t)
        self.stdout: str = ""

    def run(self):
        random.seed(self.seed)
        result = self.call()
        if any(result.exc_info):
            is_exc = (isinstance(self.expect[0], type)
                      and issubclass(self.expect[0], BaseException))
            if is_exc:
                self.passed = self.expect[0] == result.exc_info[0]
            else:
                self.exc_info = result.exc_info
            self.header += repr(result.exc_info[0])
        else:
            self.passed = self._compare(result.retval, result.stdout)
            try:
                self.header += repr(result.retval)
            except RecursionError:
                self.header += "<Error: Infinitely Recursive Data Structure>"
        if result.stdout:
            self.header += "\n  " + repr(result.stdout)
        self.header += "\n"

    def _compare(self, retval: Any, output: str) -> bool:
        # TODO: correctly handle case when expect must be empty string
        if self.expect[1] and output != self.expect[1]:
            return False
        try:
            return round(retval - self.expect[0], 7) == 0
        except TypeError:
            try:
                # order ensures expect is self for __eq__
                return self.expect[0] == retval
            except AttributeError:
                pass
        return False

    def _init_header(self, function: Callable[..., Any], args: Sequence[Any],
                     seed: int, timeout: int) -> str:
        if isinstance(function, safedef.SafeFunction):
            name = function.name
        else:
            name = function.__name__
            if function.__module__:
                name = function.__module__ + "." + name
        quote = lambda v: "\"" + v + "\"" if isinstance(v, str) else str(v)
        arg_str = ", ".join(quote(arg) for arg in args)
        expect = repr(self.expect[0]) + "\n"
        if self.expect[1]:
            expect += "  " + repr(self.expect[1]) + "\n"
        return (f"seed({seed}) {timeout}s\n"
                + f"[EXPECT] {name}({arg_str}) -> {expect}"
                + f"[ACTUAL] {name}({arg_str}) -> ")

#    def format_stdout(self):
#        diff = ""
#        if self.stdout or actual and actual[1]:
#            lines = difflib.ndiff(actual[1].splitlines(True),
#                                  self.stdout.splitlines(True))
#            lines = [line for line in lines if not line.startswith(" ")]
#            if lines:
#                diff = "\n  [OUTPUT]\n"
#                diff += textwrap.indent("".join(lines), " " * 4)
#        return self.header + diff
#
#    def _preprocess(self, s: str, ndigits: int) -> str:
#        s = self._remove_whitespace(s)
#        s = self._round_floats(s, ndigits)
#        s = self._remove_trailing_zeros(s)
#        return s
#
#    def _remove_whitespace(self, s: str) -> str:
#        s = s.strip()
#        s = re.sub(r"\s*\n\s*", r"\n", s)    # remove spaces around newlines
#        return re.sub(r"(\s)\1+", r"\1", s)  # remove multiple spaces/newlines
#
#    def _round_floats(self, s: str, ndigits: int) -> str:
#        round_match = lambda m: f"{float(m.group()):.{ndigits}f}"
#        return re.sub(r"\d+\.\d+(?:e-\d+)?", round_match, s)
#
#    def _remove_trailing_zeros(self, s: str) -> str:
##        return re.sub(r"(\d+\.)0+(?=\D)", r"\g<1>" + "0" * nzeros, s)
#        return re.sub(r"(\d+)\.0+(?=\D)", r"\1", s)
