import copy
import datetime
import os
import sys
from typing import Dict, List

from src import error
from src import utils
from src import write
from src.grade import grade
from src.grade import suite
from src.rules import access
from src.rules import langfeat
from src.rules import rules
from src.sandbox import safepkg


# TODO: read min_tests from cfg
def run(course: str, assignment: str, username: str, files: Dict[str, str],
        min_tests: int = 5, is_admin: bool = False) -> str:
    now = datetime.datetime.now()
    if not files:
        raise error.FileNamesNotSpecified(" ".join(files))
    if not _dir_exists(course, assignment):
        return "Invalid course number or assignment name\n"

    files = _update_file_paths(course, assignment, username, files)
    writer = write.Writer(files)

    config = rules.load_config(course, assignment)
    due_datetime, is_open, penalty = access.load_access(config, username, now)
    if not is_open and not is_admin:
        return f"Submission Closed: {course} {assignment}\n"

    feat_rules = langfeat.load_features(config, tuple(files))
    try:
        # TODO: add params in admin.py for skip_* options
        pkg = safepkg.SafePackage(course, assignment, files, min_tests,
                                  feat_rules, skip_lint=is_admin,
                                  skip_type=is_admin)
    except SyntaxError:
        filenames = tuple(os.path.basename(path) for path in files)
        return error.filter_traceback(filenames, *sys.exc_info())
    scores = {}
    result = {}
    if pkg.is_loaded():
        case_path = os.path.join(utils.get_top_dirname(), "cases", course,
                                 assignment, "cases.py")
        if not os.path.exists(case_path):
            return "Test cases not yet ready, try again later\n"
        # TODO: change to score, (label, total)
        scores, result = grade.run_cases(pkg, case_path, penalty)
        writer.write_scores(scores, result)
    if pkg.errors.has_any():
        writer.write_errors(pkg.errors.format_all())
    if assignment.startswith("quiz") or assignment == "final":
        threshold = 0.2
        # TODO: find out how result could be empty
        score_table = ("\n" + utils.colorize("[WARNING]", color="red")
                       + f" Total Score < {int(threshold * 100)}%"
                       if not result or result[1] < threshold else "")
    else:
        score_table = grade.format_scores(scores, result)
    is_success = False
    if pkg.is_loaded() and (grade.is_best(result[1], writer.load_scores())
                    or assignment.startswith("quiz") or assignment == "final"):
        is_success = True
        writer.finalize()
    return _join_output(pkg.errors, score_table, is_success, due_datetime)


def _dir_exists(course: str, assignment: str) -> bool:
    """Return True if directory exists and False otherwise."""
    return os.path.exists(os.path.join(utils.get_top_dirname(), "cases",
                                       course, assignment))


def _update_file_paths(course: str, assignment: str, username: str,
                       files: Dict[str, str]) -> Dict[str, str]:
    """
    Update the filenames to include the absolute path of their destination.
    """
    dirname = utils.get_temp_dirname(course, assignment, username)
    return {os.path.join(dirname, os.path.basename(filename)): source
            for filename, source in files.items()}


def _join_output(errors: error.ErrorFormatter, score_table: str,
                 is_success: bool, due_datetime: datetime.datetime) -> str:
    """
    Concatenate errors, scores, and submission status into one string.
    """
    return (errors.format_visible()
            + score_table
            + _format_status(is_success)
            + _get_due_message(due_datetime))


def _get_due_message(due_datetime: datetime.datetime) -> str:
    timedelta = due_datetime - datetime.datetime.now()
    if timedelta.days < 0:
        return ""
    days = timedelta.days
    timedelta -= datetime.timedelta(days=days)
    hours = timedelta.seconds // 3600
    timedelta -= datetime.timedelta(hours=hours)
    minutes = timedelta.seconds // 60
    return (f"Assignment is due in {days} day(s),"
            + f" {hours} hour(s), {minutes} minute(s).\n")


def _format_status(success: str, reason: str = "") -> str:
    """Create a success or failure message."""
    status = "SUCCESS" if success else "FAILURE"
    fmt_str = " Submission Status | {0} |"
    message = fmt_str.format(status)
    line = "\n" + "-" * len(message) + "\n"
    status = (utils.colorize(status, color="green") if success
              else utils.colorize(status, color="red"))
    message = fmt_str.format(status)
    return utils.colorize(line + message + line, bold=True) + "\n"
