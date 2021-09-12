import os
import re
import traceback
from typing import Dict, List, Set, Tuple, Type


ExcInfo = Tuple[Type[BaseException], BaseException,
                traceback.TracebackException]


class CaseyRuntimeError(BaseException):
    """ """


class CaseyTimeoutError(BaseException):
    """ """


class CaseyInputError(BaseException):
    """ """


class DisabledFunctionError(BaseException):
    """Raised when a disabled function attempts to be called."""


class FileNamesNotSpecified(BaseException):
    """ """


class ProhibitedFileModeError(BaseException):
    """ """


class ReturnValueIgnoredError(BaseException):
    """Raised when a submitted function fails to complete."""


class InvalidCaseFunctionError(BaseException):
    """ """




class ErrorFormatter(object):

    def __init__(self, files: Dict[str, str]) -> None:
        self._lines: Dict[str, List[str]] = \
            {os.path.basename(path): source.splitlines(True)
             for path, source in files.items()}
        self._to_print = {}
        self._to_write = {}
        self._limit: int = 10000

    def __repr__(self) -> str:
        return self.format_all()

    def __contains__(self, item: str) -> bool:
        return item in self._to_print or item in self._to_write

    def has_visible(self) -> bool:
        return bool(self._to_print)

    def has_any(self) -> bool:
        return self.has_visible() or bool(self._to_write)

    def add(self, name: str, message: str, hidden: bool = True,
            linenos: Set[int] = frozenset()) -> None:
        message = message[:self._limit]
        self._to_write.setdefault(name, {})
        self._to_write[name].setdefault(message, set()).update(linenos)
        if not hidden:
            self._to_print.setdefault(name, {})
            self._to_print[name].setdefault(message, set()).update(linenos)

    def add_traceback(self, name: str, exc_info: ExcInfo,
                      max_frames: int = 10) -> None:
        if any(exc_info):
            message = "".join(traceback.format_exception(*exc_info,
                                                         limit=max_frames))
            self._to_write.setdefault(name, {})
            self._to_write[name].setdefault(message, set())
            # TODO: prevent showing Casey code if mod_name is also a Casey module
            message = filter_traceback(tuple(self._lines), *exc_info,
                                       max_frames=max_frames)
            if message:
                self._to_print.setdefault(name, {})
                self._to_print[name].setdefault(message, set())

    def add_case(self, name: str, header: str, exc_info: ExcInfo,
                 hidden: bool = True) -> None:
        self.add(name, header, hidden=hidden)
        self.add_traceback(name, exc_info)

    def format_all(self) -> str:
        return self._format(self._to_write)

    def format_visible(self) -> str:
        return self._format(self._to_print) if self.has_visible() else ""

    def _format(self, errors) -> str:
        blocks = []
        border_size = 70
        single_line = "-" * border_size + "\n"
        double_line = "=" * border_size + "\n"
        for name in sorted(errors):
            header = double_line + f"ERROR: {name}\n" + single_line
            filename = name.split(".")[0] + ".py"
            text = ""
            for message in sorted(errors[name], key=len):
                text += message.strip() + "\n"
                for lineno in sorted(errors[name][message]):
                    # TODO: get filename from some other source
                    #       presently raises KeyError if casey.group name is
                    #       not a function
                    lines = self._lines[filename]
                    text += f"  Line {lineno:3}: {lines[lineno - 1]}"
                text += single_line
            blocks.append(header + text)
        return "\n\n".join(blocks)




def filter_traceback(filenames: Tuple[str], etype: Type[BaseException],
                     value: BaseException, tb: traceback.TracebackException,
                     max_frames: int = 10) -> str:
    """Return a string of the traceback from the given exception values."""
    if etype is None or issubclass(etype, DisabledFunctionError):
        return ""
    if isinstance(etype, TimeoutError):
        value.args = ("Timeout Loading Module",)
    frames = [frame for frame in traceback.extract_tb(tb, limit=max_frames)
              if os.path.basename(frame.filename) in filenames]
    for frame in frames:
        frame.filename = os.path.basename(frame.filename)
    summary = (traceback.StackSummary.from_list(frames).format()
               + traceback.format_exception_only(etype, value))
    if len(summary) > 1:
        summary.insert(0, "Traceback (most recent call last):\n")
    return "".join(summary)

#        source_lines = [f"{' ' * 4}{lines[frame.lineno - 1].lstrip()}"
#                        for frame in frames
#                        if frame.lineno <= len(lines)]
#        tb_lines = []
#        for i, line in enumerate(traceback.format_list(frames)):
#            if i < len(source_lines):  # TODO: remove cond when above fixed
#                tb_lines.append(line)
#                tb_lines.append(source_lines[i])
#        tb_lines += traceback.format_exception_only(etype, value)
#        # re.sub requires re-importing re which fails
#        match = re.match(r"^(?:\w+\.)*(\w+:?)", tb_lines[-1])
#        tb_lines[-1] = tb_lines[-1].replace(match.group(0), match.group(1))
#        if len(tb_lines) == 1:
#            return tb_lines[0]
#        return "Traceback (most recent call last):\n" + "".join(tb_lines)
