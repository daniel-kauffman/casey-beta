import random
import traceback
import typing
from typing import Any, Callable, List, Optional, Sequence, Tuple, Union

from src import error
from src.grade import case
from src.sandbox import safedef
from src.sandbox import safepkg
from src.sandbox import sandbox


def load_cases(case_path: str, pkg: safepkg.SafePackage) -> List[case.Case]:
    cts = CaseyTestSuite(pkg)
    with open(case_path, "r") as fp:
        exec(fp.read(), {"casey": cts, "typing": typing, "error": error,
                         "Null": safedef.Null})
    return cts.groups




class CaseyTestSuite(object):

    def __init__(self, pkg: safepkg.SafePackage) -> None:
        self.pkg: safepkg.SafePackage = pkg
        self.groups: Dict[Tuple[str, float], List[case.Case]] = {}
        self.group_key: Optional[Tuple[str, float]] = None
        self.group_fun: Optional[Callable[..., Any]] = None

    def __enter__(self):
        return self._create_case

    def __exit__(self, *args) -> bool:
        if args[0]:
            # TODO: set all cases in group to fail, display error message
            self.groups[self.group_key] = []
            traceback.print_exception(*args)
        self.group_key = None
        self.group_fun = None
        return True

    # TODO: fix to work with methods too
    def override(self, name: str, obj: Any) -> None:
        mod_name, obj_name = name.split(".", maxsplit=1)
        self.pkg[mod_name][obj_name] = obj

    def group(self, name: str, w: float = 1.0,
              f: Union[str, Callable[..., Any]] = "") -> "CaseyTestSuite":
        self.group_key = (name, w)
        try:
            self.group_fun = self._to_callable(f)
        except error.InvalidCaseFunctionError:
            try:
                self.group_fun = self._to_callable(name)
            except NotImplementedError:
                self.group_fun = \
                    safedef.SafeFunction.not_implemented(name, self.pkg.sandbox)
            except error.InvalidCaseFunctionError:
                pass
        self.groups.setdefault(self.group_key, [])
        return self

    def capture(self, name: str, *args, i: str = "", s: Optional[int] = None,
                t: int = 0, **kwargs) -> safedef.SafeFunctionResult:
        """Return the call's return value and stdout string."""
        if s is not None:
            random.seed(s)
        mod_name, def_name = name.split(".", maxsplit=1)
        safefun = self.pkg[mod_name][def_name]
        return safefun.capture(*args, _stdin=i, _timeout=t, **kwargs)

    def call(self, name: str, *args, i: str = "", s: Optional[int] = None,
             t: int = 0, **kwargs) -> safedef.SafeFunctionResult:
        """Return the call's return value and stdout string."""
        return self.capture(name, *args, i=i, s=s, t=t, **kwargs).validate()

    # TODO: sandbox class methods
    #       raise warning if calling directly in cases.py (until safe)
    def make(self, name: str, *args, req_attrs: Tuple[str, ...] = (),
             restrict: bool = True, **kwargs) -> Any:

        # TODO: sandbox methods and remove
        mod_name, cls_name = name.split(".", maxsplit=1)
        obj = self.pkg[mod_name][cls_name](*args, **kwargs)


        missing = set(req_attrs) - set(obj.__dict__)
        if missing:
            msg = "Class attribute(s) not found: " + ", ".join(missing)
            raise Exception(msg)
        if restrict and req_attrs:
            extra = set(obj.__dict__) - set(req_attrs)
            if extra:
                raise AttributeError("Extra attribute(s): " + ", ".join(extra))
        return obj

    def equals(self, actual: Any, expect: Any, **kwargs) -> None:
        self._create_case((actual,), expect, f=lambda _:_, **kwargs)

    def _to_callable(self, f: Union[str, Callable[..., Any]]
    ) -> safedef.SafeFunction:
        if isinstance(f, str):
            try:
                mod_name, def_name = f.split(".", maxsplit=1)
            except ValueError:
                raise error.InvalidCaseFunctionError(f)
            f = self.pkg[mod_name][def_name]
        if not callable(f):
            raise error.InvalidCaseFunctionError(f)
        if not f.__module__:
            f.__module__ = "cases"
        if isinstance(f, safedef.SafeFunction):
            return f
        return safedef.SafeFunction(f, self.pkg.sandbox, use_disable=False)

    def _create_case(self, args: Sequence[Any], expect: Any, **kwargs) -> None:
        try:
            f = self._to_callable(kwargs.pop("f", ""))
        except error.InvalidCaseFunctionError as e:
            if self.group_fun:
                f = self.group_fun
            else:
                raise e
        testcase = case.Case(f, args, expect, **kwargs)
        self.groups[self.group_key].append(testcase)
