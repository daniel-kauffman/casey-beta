import json
import os
import re
from typing import Dict, List, Tuple

from mypy import api
from pylint import epylint

from src import error
from src import utils


def check_style(errors: error.ErrorFormatter, course: str, assignment: str,
                paths: Tuple[str, ...]) -> None:
    cfg_path = _get_cfg_path(course, assignment, "pylint.cfg")
    for error in _make_report(paths, cfg_path):
        name = error["module"]
        if error["obj"]:
            name += "." + error["obj"]
        message = f"[pylint:{error['symbol']}]\n" + error["message"]
        errors.add(name, message, hidden=False, linenos={int(error["line"])})


def _make_report(paths: Tuple[str, ...], cfg_path: str) -> Dict[str, str]:
    arg_str = " ".join(paths) + f" --rcfile={cfg_path}"
    stdout = epylint.py_run(arg_str, return_std=True)[0].getvalue()
    if not stdout:
        return {}
    return json.loads(stdout)


def check_types(errors: error.ErrorFormatter, course: str, assignment: str,
                paths: Tuple[str, ...]) -> None:
    cfg_path = _get_cfg_path(course, assignment, "mypy.cfg")
    report = _run_mypy(paths, cfg_path)
#    _parse_module_errors(errors, report)
    _parse_function_errors(errors, report)


def _run_mypy(paths: Tuple[str, ...], cfg_path: str) -> List[str]:
    args = list(paths) + ["--config-file", cfg_path, "--no-strict-optional",
                          "--no-incremental"]
    return api.run(args)[0]


def _parse_module_errors(errors: error.ErrorFormatter, report: str) -> None:
    """
    Format of line:
        <path>:<lineno>: error: <message>
    """
    pass


def _parse_function_errors(errors: error.ErrorFormatter, report: str) -> None:
    """
    Parse the mypy report for type errors in each function's signature. Ignore
    type errors involving the interchange of int and float types.

    The errors are contained in pairs of lines in the report. The first line in
    the pair identifies the function name while the second line in the pair
    provides the error message.

    Format of line pair:
        <path>: note: In function "<name>":
        <path>:<lineno>: error: <message>
    """
    pattern = re.compile(r"^.*?(\w+)\.py: note: In function \"(\w+)\":\n"
                         + r"^.*?\1\.py:(\d+): error: (.*?)\s+\[(.*?)\]\n",
                         re.MULTILINE)
    ignore = re.compile(r"^Incompatible types in assignment "
                        + r"\(expression has type \"(?:int|float)\", "
                        + r"variable has type \"(?:int|float)\"\)$")
    for modname, function, lineno, message, code in re.findall(pattern, report):
        if not re.match(ignore, message):
            name = modname + "." + function
            message = f"[mypy:{code}]\n" + message
            errors.add(name, message, hidden=False, linenos={int(lineno)})


def _get_cfg_path(course: str, assignment: str, filename: str) -> str:
    parent = utils.get_top_dirname()
    paths = [os.path.join(parent, "cases", course, assignment, filename),
             os.path.join(parent, "cases", course, filename),
             os.path.join(parent, "cases", filename)]
    for path in paths:
        if os.path.exists(path):
            return path
    raise FileNotFoundError
