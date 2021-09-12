import cProfile
import os
import pstats
import re
import signal
import textwrap
from typing import Any, Callable

from src import error
from src import utils
from src.sandbox.ctxman import disable


class Timer(object):

    def __init__(self, dirname: str, seconds: int = 1) -> None:
        self.seconds: int = seconds
        self.has_expired: bool = False
        self.profiler: cProfile.Profile = cProfile.Profile()
        self.dirname = dirname
        signal.signal(signal.SIGVTALRM, self._handle_signal)

    def __enter__(self) -> "Timer":
        self.profiler.enable()
        self._set_timer(self.seconds)
        return self

    def __exit__(self, *args) -> None:
        self._reset_timer()
        self.profiler.disable()
        self.profiler.clear()

    def set_timeout(self, seconds: int) -> None:
        self.seconds = seconds

    def _set_timer(self, seconds: int):
        self.has_expired = False
        signal.setitimer(signal.ITIMER_VIRTUAL, seconds)

    def _reset_timer(self):
        self._set_timer(0.0)

#    @disable.suspend
    def _handle_signal(self, *args):
        self.profiler.disable()
        self.has_expired = True
        stats = self._gather_stats()
        msg = f"Process exceeded {self.seconds} second(s)"
        if stats:
            msg += "\n\n" + stats
        raise error.CaseyTimeoutError(msg)

    def _gather_stats(self) -> str:
        selected = {}
        with open(os.devnull) as devnull:
            stats = pstats.Stats(self.profiler, stream=devnull).stats
            for (path, _, name), (_, ncalls, tottime, _, _) in stats.items():
                tottime = round(tottime, 2)
                if tottime > 0:
                    name = self._qualify_name(path, name)
                    if name == "[casey overhead]":
                        selected.setdefault(name, (0, 0))
                        selected[name] = (0, selected[name][1] + tottime)
                    else:
                        selected[name] = (ncalls, tottime)
        return self._format_stats(selected)

    def _qualify_name(self, path: str, name: str) -> str:
        if path == "<string>":  # path is cases file
            return name
        if path.strip("/").startswith(utils.get_top_dirname().strip("/")):
            return "[casey overhead]"
        match = re.match(r"<built-in method (\w+)\.(\w+)>", name)
        if match:
            if match.group(1) == "builtins":
                return match.group(2)
            return match.group(2) + "." + match.group(1)
        match = re.match(r"<method '(\w+)' of '([\w.]+)' objects>", name)
        if match:
            return match.group(2) + "." + match.group(1)
        match = re.match(r"/usr/lib64/python\d+\.\d+/(\w+).py", path)
        if match:
            return match.group(1) + "." + name
        return name if os.path.dirname(path) == self.dirname else ""

    def _format_stats(self, stats) -> str:
        if not stats:
            return ""
        width = len(max(stats, key=lambda s: len(s)))
        fmt_str = "{0:>" + str(width) + "} | {1:>9} | {2:>7{3}}\n"
        output = fmt_str.format("Function", "Calls", "Seconds", "")
        output += "-" * (len(output) - 1) + "\n"
        names = sorted(stats, key=lambda n: stats[n][1], reverse=True)
        for name in names:
            ncalls, tottime = stats[name]
            output += fmt_str.format(name, ncalls, tottime, ".2f")
        return textwrap.indent(output, " " * 2)
