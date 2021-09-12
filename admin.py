import argparse
import glob
import json
import os

from src import casey
from src import utils


def main():
    args = get_args()
    if args.csv:
        compile_csv(args.course)
    else:
        filenames = utils.get_filenames(args.course, args.assignment)
        files = {}
        for filename in filenames:
            file_path = os.path.join(os.getcwd(), filename)
            if not os.path.exists(file_path):
                print("File Not Found:", file_path)
            else:
                with open(file_path) as fp:
                    files[filename] = fp.read()
        print(casey.run(args.course, args.assignment, args.username, files,
                        min_tests=args.min_tests, is_admin=args.admin),
              end="")


def get_args():
    parser = argparse.ArgumentParser(description=
    """Casey Administrator Program""")
    parser.add_argument("course")
    parser.add_argument("assignment")
    parser.add_argument("-a", "--admin", action="store_true")
    parser.add_argument("-c", "--csv", action="store_true")
    parser.add_argument("-t", "--min-tests", type=int, default=5)
    parser.add_argument("-u", "--username", default=utils.get_admin_name())
    return parser.parse_args()


def compile_csv(course: str) -> None:
    scores = {}
    top_dirname = os.path.join(os.environ["HOME"], "inbox")
    assignments = sorted(os.listdir(os.path.join(top_dirname, course)))
    usernames = {os.path.basename(path) for path in
                 glob.glob(os.path.join(top_dirname, course, "*", "*"))}
    for assignment in assignments:
        for username in usernames:
            scores.setdefault(username, [])
            scores[username].append(load_score(course, assignment, username))
    print(",".join(["username"] + assignments))
    for username, items in scores.items():
        print(",".join([username] + [f"{i:.3f}" for i in items]))


def load_score(course: str, assignment: str, username: str) -> float:
    json_path = os.path.join(os.environ["HOME"], "inbox",
                             course, assignment, username, "scores.json")
    if not os.path.exists(json_path):
        return 0.0
    key = "[TOTAL]"
    with open(json_path) as fp:
        score = json.load(fp)
        try:
            if key in score:
                return float(score[key])
            return float(score[key + "[LATE]"])
        except KeyError:
            raise KeyError(f"{course} {assignment} {username}")


if __name__ == "__main__":
    main()
