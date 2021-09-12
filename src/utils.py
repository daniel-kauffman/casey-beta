import configparser
import os
import pwd
import re
from typing import List


def secure_filename(filename: str) -> str:
    """Return a sanitized file name."""
    return utils.secure_filename(filename)


def get_admin_name() -> str:
    """Return the username of the owner of the server process."""
    return pwd.getpwuid(os.getuid()).pw_name


def get_basename(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def get_root_dirname() -> str:
    dirname = os.path.join(os.environ["HOME"], "inbox")
    if not os.path.exists(dirname):
        raise FileNotFoundError(dirname)
    return dirname


def get_submit_dirname(course: str, assignment: str, username: str) -> str:
    return os.path.join(get_root_dirname(), course, assignment, username)


def get_temp_dirname(course: str, assignment: str, username: str) -> str:
    return os.path.join(get_submit_dirname(course, assignment, username), "tmp")


def get_top_dirname() -> str:
    pattern = re.compile(os.path.join(os.environ["HOME"], r".*?" + os.sep))
    return re.search(pattern, os.sep + __file__).group()


def get_assignment_dirname(course: str, assignment: str) -> str:
    return os.path.join(get_top_dirname(), "cases", course, assignment)


def get_cases_path(course: str, assignment: str) -> str:
    return os.path.join(get_assignment_dirname(course, assignment), "cases.py")


def get_filenames(course: str, assignment: str) -> List[str]:
    cfg_name = "rules.cfg"
    path = os.path.join(get_assignment_dirname(course, assignment), cfg_name)
    if not os.path.exists(path):
        return []
    config = configparser.ConfigParser(allow_no_value=True)
    config.optionxform = str  # make file names case-sensitive
    config.read(path)
    return list(config["files"]) if config.has_section("files") else []


def colorize(chars: str, color: str = "reset", bold: bool = False) -> str:
    colors = {  "red": "\033[31m",
              "green": "\033[32m",
              "reset": "\033[39m"}
    if color not in colors:
        raise KeyError("Color Not Supported")
    chars = colors[color] + chars + colors["reset"]
    if bold:
        chars = "\033[1m" + chars + "\033[0m"
    return chars
