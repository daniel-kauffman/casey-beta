import ast
import copy
import importlib
import io
import re
import sys
import types
from typing import Any, Callable, Dict, List, Tuple

import coverage

from src.sandbox import safedef
from src.sandbox import safemod
from src.static import defparse


class CallMonitor(object):

    def __init__(self, safemods: List[safemod.SafeModule]) -> None:
        use_branch: bool = False  # TODO: move to config
        self.safemods: List[safemod.SafeModule] = \
            [sm for sm in safemods if sm.module and not sm.is_suite]
        self.calls: Dict[str, FunctionCall] = {}
        self.cov = coverage.Coverage(data_file=None, cover_pylib=False,
                                     branch=use_branch)
        self.functions: Dict[str, safedef.SafeFunction] = {}

    def __enter__(self) -> "CallMonitor":
        self.cov.start()
        for sm in self.safemods:
            # sm.reload()  # allow coverage to measure definitions
            for name in sm.nodes:
#                if "." in name:  # is method
#                    cls_name, obj_name = name.split(".")
#                    self.functions[name] = \
#                        sm.module.__dict__[cls_name].__dict__[obj_name]
#                    setattr(sm.module.__dict__[cls_name], obj_name,
#                            self._monitor(self.functions[name]))
                self.functions[name] = sm[name]
                sm[name] = self._monitor(self.functions[name])
        return self

    def __exit__(self, *args) -> bool:
        self.cov.stop()
        for sm in self.safemods:
            for name in sm.nodes:
#                if "." in name:
#                    pass  # TODO
#                    cls_name, obj_name = name.split(".")
#                    setattr(sm.module.__dict__[cls_name], obj_name,
#                            self.functions[name])
                sm[name] = self.functions[name]

    def validate_calls(self, sm: safemod.SafeModule,
                       min_calls: int) -> List[Tuple[str, str]]:
        insufficient = []
        for def_name, node in sm.nodes.items():

            if "Node" not in def_name:

                count = len(self.calls.get(def_name, {}))
                unique_retvals = []  #self._get_unique_return_values(def_name)
                if min_calls > 1 and len(unique_retvals) == 1:
                    message = f"Insufficient unique return values"
                    insufficient.append((def_name, message))
                elif _is_testable(node) and count < min_calls:
                    message = ("Insufficient successful tests"
                               + f" [{count}/{min_calls}]")
                    insufficient.append((def_name, message))
        return insufficient

    def _get_unique_return_values(self, name: str):
        unique_retvals = []
        for _, _, result in self.calls.get(name, {}):
            contains = False
            for retval in unique_retvals:
                try:
                    if retval == result.retval:
                        contains = True
                except AttributeError:
                    pass
            if not contains:
                unique_retvals.append(result.retval)
        return unique_retvals

    def get_analysis(self):
        modules = [sm.module for sm in self.safemods]
        with io.StringIO() as stream:
            self.cov.report(modules, file=stream, show_missing=True)
            print(stream.getvalue())
#        return self.cov.analysis(module)

    def get_coverage(self, module: types.ModuleType) -> str:
        pattern = re.compile(r"(\d+)\%\s*(.*)")
        with io.StringIO() as stream:
            self.cov.report([module], file=stream, show_missing=True)
            match = re.search(pattern, stream.getvalue())
        percent = int(match.group(1))
        if percent == 100:
            return ""
        return "\nLines Not Tested:\n  {0}\n".format(match.group(2).strip())

    def _monitor(self, sf: safedef.SafeFunction):
        def _(*args, **kwargs):
#            call = [copy.deepcopy(args), tuple(copy.deepcopy(kwargs).items())]
            caller = sys._getframe(1).f_code.co_name
            call = FunctionCall(sf.name, args, kwargs, caller)
            try:
                call.set_result(sf(*args, **kwargs))
            finally:
                self.calls.setdefault(sf.name, [])
#                call.append(result)
#                if call not in self.calls[sf.name]:
#                if call not in self.calls[sf.name] and call.is_unittest:
                if (call not in self.calls[sf.name] or sf.name.startswith("pset8.")) and call.is_unittest:
                    self.calls[sf.name].append(call)
                return call.result
        return _




class FunctionCall(object):

    def __init__(self, name: str, args: Tuple[Any], kwargs: Dict[str, Any],
                 caller: str) -> None:
        self.args: Tuple[Any] = copy.deepcopy(args)
        self.kwargs: Tuple[Any] = tuple(copy.deepcopy(kwargs).items())
        self.result: Optional[Any] = None
        self.is_unittest: bool = self.verify_caller(name, caller)

    def __eq__(self, other: "FunctionCall") -> bool:
        return self.args == other.args and self.kwargs == other.kwargs

    def verify_caller(self, name: str, caller: str) -> bool:
        _, def_name = name.rsplit(".", maxsplit=1)
        return bool(re.match(fr"test_{def_name}_", caller))

    # TODO: work with methods (safecls)
    def set_result(self, result: Any) -> None:
        self.result = (result.retval
                       if isinstance(result, safedef.SafeFunctionResult)
                       else result)


# TODO: methods or functions that mutate are testable
def _is_testable(root: ast.FunctionDef) -> bool:
    exclude = ["main", "__init__"]
    if root.name in exclude:
        return False
    calls = set(defparse.parse_calls(root))
    if {"input", "open", "hash"} & calls:
        return False
#    if defparse.parse_keywords(root).get("return"):
#        return True
    return True
