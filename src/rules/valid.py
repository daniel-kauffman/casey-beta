import ast
import re
from typing import Dict, List, Set, Tuple

from src import error
from src.rules import langfeat
from src.sandbox import safemod
from src.static import analysis
from src.static import defparse
from src.static import modparse


def validate_package(course: str, assignment: str, files: Dict[str, str],
                     feat_rules: langfeat.FeatRules,
                     safemods: List[safemod.SafeModule],
                     skip_lint: bool, skip_type: bool) -> error.ErrorFormatter:
    """
    Run linting (with pylint) and type checking (with mypy) on the package
    and return the aggregated errors.
    """
    errors = error.ErrorFormatter(files)
    mod_names = tuple(sm.name for sm in safemods)
    if not skip_lint:
        analysis.check_style(errors, course, assignment, tuple(files))
    if not skip_type:
        analysis.check_types(errors, course, assignment, tuple(files))
    for sm in safemods:
        _validate_module(errors, sm, feat_rules, mod_names)
    return errors


def _validate_module(errors: error.ErrorFormatter, sm: safemod.SafeModule,
                     feat_rules: langfeat.FeatRules,
                     mod_names: Tuple[str, ...]) -> None:
    """
    Return any module-level errors, defined as the following:
        - Invalid header
        - Prohibited imports
        - Global code (if disallowed)
    """
    message, linenos = _validate_header(sm.source, sm.lines)
    if message:
        errors.add(sm.name, message, hidden=False, linenos=linenos)
    for message, linenos in _validate_imports(sm, feat_rules).items():
        errors.add(sm.name, message, hidden=False, linenos=linenos)
    globals_found = modparse.parse_globals(sm.root)
    if not sm.is_suite and globals_found:
        errors.add(sm.name, "Global(s)", hidden=False, linenos=globals_found)
    for def_name, node in sm.nodes.items():
        for message, linenos in _validate_function(def_name, node, feat_rules,
                                                   mod_names).items():
            errors.add(def_name, message, hidden=False, linenos=linenos)


def _validate_header(source: str, lines: List[str]) -> Tuple[str, Set[int]]:
    """
    Determine whether the header at the top of the module matches the
    required format.

        # Name:         First Last
        # Course:       CSC/CPE ###
        # Instructor:   First Last
        # Assignment:   Any Name
        # Term:         Summer/Fall/Winter/Spring 20##
    """
    linenos = sorted(modparse.parse_header(source))
    if not linenos:
        return ("Header not found", set())
    header = "".join(lines[linenos[0] - 1:linenos[-1]])
    if not header.strip():
        return ("Header not found", set())
    terms = ["Fall", "Winter", "Spring", "Summer"]
    pattern = ( r"(?:# Name:\s*?(?:[\s+\-][A-Z][A-Za-z']+){2,}\s*\n)+" +
                r"# Course:\s+(?:CSC|CPE) \d{3}(?:-\d+)?\s*\n" +
                r"# Instructor:\s+(?:[A-Z][a-z]*\.? ?){1,2}\s*\n" +
                r"# Assignment:\s+.*?\n" +
               fr"# Term:\s+(?:{'|'.join(terms)}) (?:20\d\d)\s*\n")
    if re.match(pattern, header):
        return ("", set())
    return ("Invalid header format", linenos)


# TODO: allow Any in rules.cfg
def _validate_imports(sm: safemod.SafeModule,
                      feat_rules: langfeat.FeatRules) -> Dict[str, Set[int]]:
    """
    Ensure that all module imports are permitted by the course or
    assignment rules.
    """
    errors = {}
    imports = modparse.parse_imports(sm.root)
    for name, linenos in imports.items():
#            if name.startswith("typing."):
#                _, annotation = name.split(".")
#                if annotation not in annotations:
#                    msg = "Prohibited annotation(s)"
#                    errors.setdefault(msg, set()).extend(linenos)
        if name not in tuple(feat_rules["imports"]):
            errors.setdefault("Prohibited import(s)", set()).update(linenos)
    return errors


def _validate_function(name: str, root: ast.FunctionDef,
                       feat_rules: langfeat.FeatRules,
                       mod_names: Tuple[str, ...]) -> Dict[str, Set[int]]:
    errors = {}
    parsed = {"calls": defparse.parse_calls(root),
              "exceptions": defparse.parse_exceptions(root),
              "keywords": defparse.parse_keywords(root),
              "operators": defparse.parse_operators(root),
              "types": defparse.parse_types(root)}
    for category in parsed:
        for feature, linenos in parsed[category].items():
            if not _is_allowed(category, feature, name, feat_rules, mod_names):
                message = _label(category, feature, "prohibited")
                errors[message] = linenos
#        for feature, functions in feat_rules[category].items():
#            linenos = parsed[category].get(feature, set())
#            req_range = functions.get(name, {})
#            if req_range and len(linenos) not in req_range:
#                fmt_str = "requires [{0}] use(s)"
#                if req_min == req_max != len(linenos):
#                    message = fmt_str.format(req_min)
#                elif len(linenos) not in req_range:
#                    message = fmt_str.format(f"{req_min} - {req_max}")
#                elif req_min > 0 and len(linenos) < req_min:
#                    message = fmt_str.format(f">= {req_min}")
#                elif req_max >= 0 and len(linenos) > rule_max:
#                    message = fmt_str.format(f"<= {req_max}")
#                errors[_label(category, feature, message)] = linenos
    errors.update(_validate_recursion(name, feat_rules, parsed["calls"]))
    return errors


def _is_allowed(category: str, feature: str, def_name: str,
                feat_rules: langfeat.FeatRules,
                mod_names: Tuple[str, ...]) -> bool:
    if category == "calls" and feature not in feat_rules[category]:

        if feature.startswith("."):  # TODO: remove
            return True

        for mod_name in mod_names:
            if f"{mod_name}.{feature}" in feat_rules[category]:
                feature = f"{mod_name}." + feature
        type_names = ("dict", "list", "set", "str", "tuple",
                      "queue.PriorityQueue")
        for type_name in type_names:
            method_name = feature.rsplit(".", maxsplit=1)[-1]
            if f"{type_name}.{method_name}" in feat_rules[category]:
                feature = f"{type_name}." + method_name
    return (feature in feat_rules[category]
            and (len(feat_rules[category][feature]) == 0
                 or def_name in feat_rules[category][feature]))


def _label(category: str, feature: str, message: str) -> str:
    return f"[{category.rstrip('s')}:{feature}] {message}"


def _validate_exceptions(root: ast.FunctionDef) -> Dict[str, Set[int]]:
    exceptions = defparse.parse_exceptions(root)
    return {_label("exceptions", exc_name, "prohibited"): linenos
            for exc_name, linenos in exceptions.items()}


def _validate_recursion(def_name: str, feat_rules: langfeat.FeatRules,
                        parsed_calls: Dict[str, Set[int]]
) -> Dict[str, Set[int]]:
    if "recursion" not in feat_rules["paradigm"]:
        if def_name in parsed_calls:
            message = _label("recursion", def_name, "prohibited")
            return {message: parsed_calls[def_name]}
    return {}
