import datetime
import glob
import hashlib
import json
import os
import pprint
import time
import traceback
from typing import Tuple

import flask
import werkzeug

from src import casey
from src import utils
from src.grade import grade
from typing import Set


app = flask.Flask(__name__)


class Lock(object):

    def __init__(self, course: str, assignment: str, username: str) -> None:
        dirname = utils.get_submit_dirname(course, assignment, username)
        os.makedirs(dirname, mode=0o700, exist_ok=True)
        self.path = os.path.join(dirname, ".lock")

    def __enter__(self) -> "Lock":
        if self.get_duration() >= 15:
            os.remove(self.path)
        with open(self.path, "x") as fp:
            pass

    def __exit__(self, *args) -> bool:
        if args[0] is not FileExistsError and os.path.exists(self.path):
            os.remove(self.path)

    def get_duration(self) -> int:
        """Return the number of minutes that the lock has been active."""
        return (-1 if not os.path.exists(self.path)
                else int(time.time() - os.path.getmtime(self.path)) // 60)




@app.route("/<owner>/<course>/<assignment>/", methods=["GET"])
def get_filenames(owner: str, course: str, assignment: str) -> str:
    _validate_request(owner)
    filenames = utils.get_filenames(course, assignment)
    if not filenames:
        return ""
    return " ".join(filenames) + "\n"


@app.route("/<owner>/<username>/<key>/<course>/<assignment>/", methods=["POST"])
def receive_files(owner: str, course: str, assignment: str, username: str,
                  key: str) -> str:
    try:
        _validate_request(owner, username=username, key=key)
        files = {}
        for fp in flask.request.files.values():
            filename = werkzeug.utils.secure_filename(fp.filename)
            if not _is_valid_ext(filename):
                raise Exception(f"Invalid file type: {filename}")
            files[filename] = fp.read().decode()
        with Lock(course, assignment, username):
            return casey.run(course, assignment, username, files)
    except FileExistsError:
        return (f"[{username}] has an active submission.\n"
                "Please wait until it completes and try again.\n")
    except:
        with open("log.txt", "a") as fp:
            fp.write(f"[{datetime.datetime.now()}] {username}\n")
            fp.write(traceback.format_exc() + "\n" * 4)
        return ("Casey encountered an unexpected error.\n" +
                "Please contact your instructor for assistance.\n")


def _validate_request(owner: str, username: str = "", key: str = "") -> None:
    """Compare client/server owner's username and validate key."""
    if owner != os.environ["USER"]:
        raise Exception("Incorrect server process")
    if key and not _validate_key(username, key):
        raise Exception("Unrecognized submission protocol")


def _validate_key(username: str, key: str, key_file: str = "key.txt") -> bool:
    """Return True if key is valid False otherwise."""
    now = datetime.datetime.now()
    hash_fun = hashlib.sha512()
    hash_fun.update(username.encode())
    hash_fun.update(f"{now.year:04}/{now.month:02}/{now.day:02}".encode())
    with open(os.path.join(os.curdir, key_file), "r") as fp:
        hash_fun.update(fp.readline().strip().encode())
    return key == hash_fun.hexdigest()


def _is_valid_ext(filename: str, exts: Tuple[str] = (".py", )) -> bool:
    """Return True if file has valid extension and False otherwise."""
    return os.path.splitext(filename)[1] in exts


@app.route("/<owner>/<username>/<key>/<course>/", methods=["GET"])
def get_scores(owner: str, username: str, key: str, course: str) -> str:
    try:
        _validate_request(owner, username=username, key=key)
        paths = glob.glob(os.path.join(utils.get_root_dirname(), course, "*",
                                       username, "scores.json"))
        totals = {}
        for path in paths:
            assignment = os.path.basename(os.path.dirname(os.path.dirname(path)))

            if assignment not in []:  # TODO: move to config

                with open(path, "r") as fp:
                    total = int(grade.get_total(json.load(fp)) * 100)
                    totals[assignment] = f"{total}%"
        table = str.maketrans({"{": " ", "}": "\n", "'": "", ",": ""})
        return pprint.pformat(totals).translate(table)
    except Exception as e:
#        return repr(e)
        return "Casey summary error\n"


if __name__ == "__main__":
    app.run(port=5005)
