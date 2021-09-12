import configparser
import os

from src import utils


def load_config(course: str, assignment: str) -> configparser.ConfigParser:
    dirname = utils.get_top_dirname()
    paths = [os.path.join(dirname, "cases", "defaults.cfg"),
             os.path.join(dirname, "cases", course, "defaults.cfg"),
             os.path.join(dirname, "cases", course, assignment, "rules.cfg")]
    config = _read_file(paths[0])
    for path in paths[1:]:
        precedent = _read_file(path)
        for section in precedent:
            config[section] = precedent[section]
    return config


def _read_file(path: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser(allow_no_value=True, delimiters=(":",))
    config.optionxform = str  # make file names case-sensitive
    with open(path, "r") as fp:
        config.read_file(fp)
    return config
