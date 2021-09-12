import filecmp
import json
import os
import shutil
from typing import Dict, Optional, Tuple


class Writer:

    def __init__(self, files: Dict[str, str]) -> None:
        self.scores_filename = "scores.json"
        self.dirname = os.path.dirname(tuple(files)[0])
        self._write_files(files)

    def load_scores(self) -> Optional[Dict[str, float]]:
        path = os.path.join(os.path.dirname(self.dirname), self.scores_filename)
        if os.path.exists(path):
            with open(path, "r") as fp:
                return json.load(fp)

    def write_scores(self, scores: Dict[str, float],
                     result: Tuple[str, float]) -> bool:
        path = os.path.join(self.dirname, self.scores_filename)
        if os.path.exists(path):
            Writer._remove(path)
        scores = {name: score for (name, _), score in scores.items()}
        scores.update({result[0]: result[1]})
        if os.path.exists(os.path.dirname(path)):
            with open(path, "w") as fp:
                json.dump(scores, fp, indent=2)
            os.chmod(path, 0o600)
        return os.path.exists(path)

    def write_errors(self, errors: str) -> bool:
        path = os.path.join(self.dirname, "errors.txt")
        return Writer._write(path, errors)

    def finalize(self) -> bool:
        parent = os.path.dirname(self.dirname)
        ignore = list(filecmp.DEFAULT_IGNORES)
        Writer._remove(os.path.join(parent, "errors.txt"))
        for filename in os.listdir(self.dirname):
            if os.path.isdir(filename):
                ignore.append(filename)
            else:
                try:
                    shutil.copy2(os.path.join(self.dirname, filename), parent)
                except IsADirectoryError:
                    pass
        uncopied = filecmp.dircmp(self.dirname, parent, ignore=ignore).left_only
        if not uncopied:
            Writer._remove(self.dirname)
            return True
        return False

    def _write_files(self, files: Dict[str, str]) -> bool:
        exists = []
        os.makedirs(self.dirname, mode=0o700, exist_ok=True)
        for path, source in files.items():
            exists.append(Writer._write(path, source))
        return all(exists)

    @staticmethod
    def _write(path: str, text: str, mode: int = 0o600) -> bool:
        if os.path.exists(path):
            Writer._remove(path)
        with open(path, "w") as fp:
            fp.write(text)
        os.chmod(path, mode)
        return os.path.exists(path)

    @staticmethod
    def _remove(path: str) -> bool:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        return not os.path.exists(path)
