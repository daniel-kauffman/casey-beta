from typing import Dict, Optional, Tuple

from src import error
from src.grade import suite
from src.sandbox import safepkg


def run_cases(pkg: safepkg.SafePackage, case_path: str,
              penalty: float) -> Tuple[Dict[str, float], Tuple[str, float]]:
    """
    Side-effects: Adds any errors encountered to pkg.errors.
    """
    weighted_scores = {}
    cases = suite.load_cases(case_path, pkg)
    # TODO: raise error on duplicate case names
    for (name, weight), cases in cases.items():
        if not cases:
            pkg.errors.add(name, "Test cases not yet ready, try again later",
                           hidden=False)
            weighted_scores[(name, weight)] = 0
        else:
            n_pass = 0
            for case in cases:
                case.run()
                if case.passed:
                    n_pass += 1
                else:
                    pkg.errors.add_case(name, case.header, case.exc_info,
                                        case.hidden)
            weighted_scores[(name, weight)] = n_pass / len(cases)
    return weighted_scores, _get_result(weighted_scores, penalty)


def get_total(scores: Dict[str, float]) -> float:
    try:
        return scores["[TOTAL]"]
    except KeyError:
        return scores["[TOTAL][LATE]"]


def is_best(current_total: float, previous: Optional[Dict[str, float]]) -> bool:
    if not previous:
        return True
    return current_total >= get_total(previous)


def format_scores(weighted_scores, result: Tuple[str, float]) -> str:
    if not weighted_scores:
        return ""
    weighted_scores = _remove_shared_prefix(weighted_scores)
    width = len(max(weighted_scores, key=lambda s: len(s[0]))[0]) + 1
    fmt_str = "{0:>" + str(width) + "} | {1:>3}%"
    lines = []
    for (name, weight), score in weighted_scores.items():
        line = fmt_str.format(name, int(score * 100))
        if weight != 1.0:
            line += f" [{weight:.1f}]"
        lines.append(line)
    lines.append("-" * len(max(lines, key=len)))
    lines.append(fmt_str.format(result[0], int(result[1] * 100)))
    return "\n" + "\n".join(lines) + "\n"


def _remove_shared_prefix(weighted_scores: Dict[Tuple[str, int], float]
) -> Dict[Tuple[str, int], float]:
    prefix = list(weighted_scores)[0][0].split(".", maxsplit=1)[0] + "."
    if all(name.startswith(prefix) for (name, _) in weighted_scores):
        weighted_scores = {(name.replace(prefix, ""), weight): score
                           for (name, weight), score in weighted_scores.items()}
    return weighted_scores


def _get_result(weighted_scores: Dict[Tuple[str, int], float],
                penalty: float) -> Dict[str, float]:
    label = "[TOTAL]"
    if penalty:
        label += "[LATE]"
    return label,  _calculate_weighted_total(weighted_scores) * (1 - penalty)


def _calculate_weighted_total(weighted_scores: Dict[Tuple[str, int], float]
) -> float:
    total = 0.0
    weight_sum = 0.0
    for (_, weight), score in weighted_scores.items():
        weight_sum += weight
        total += score * weight
    return total / weight_sum
