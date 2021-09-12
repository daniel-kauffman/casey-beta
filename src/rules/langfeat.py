import configparser
import copy
import os
import re
import sys
from typing import Dict, Iterable, Tuple


# category -> feature -> object -> range
FeatRules = Dict[str, Dict[str, Dict[str, Iterable[int]]]]


def load_features(config: configparser.ConfigParser,
                  paths: Tuple[str, ...]) -> FeatRules:
    feat_rules = {"calls": {}, "keywords": {}, "imports": {}, "operators": {},
                  "paradigm": {}, "types": {}}
    for section in config.sections():
        category = section.strip().split(":")[0].lower()
        if any(category.startswith(cat) for cat in feat_rules):
            if ":" not in section:
                features = []
                for feature in config.options(section):
                    features += _expand_feature(category, feature.strip())
                for feature in features:
                    feat_rules[category][feature] = {}
            else:
                features = []
                for feature in section.split(":", maxsplit=1)[1].split(","):
                    features += _expand_feature(category, feature.strip())
                for feature in features:
                    feat_rules[category][feature] = {}
                    for def_name in config.options(section):
                        req_range = _get_range(config, category, feature)
                        feat_rules[category][feature][def_name] = req_range
    feat_rules = update_features(feat_rules, "imports",
                                 _get_user_modules(paths))
    feat_rules = update_features(feat_rules, "imports",
                                 _get_annotations(tuple(feat_rules["types"])))
    # allow type casting
    feat_rules = update_features(feat_rules, "calls",
                                 tuple(feat_rules["types"]))
    if any(feature.startswith("typing.") for feature in feat_rules["imports"]):
        feat_rules["imports"].setdefault("typing", {})
    return feat_rules


def update_features(feat_rules: FeatRules, category: str,
                    features: Tuple[str, ...]) -> FeatRules:
    feat_rules = copy.deepcopy(feat_rules)
    for feature in features:
        if category == "calls" and re.match(r"\w+\.__\w+__", feature):
            if feature.endswith("__init__"):
                feat_rules[category].setdefault(feature.split(".")[0], {})
        else:
            feat_rules[category].setdefault(feature, {})
    return feat_rules


def _expand_feature(category: str, feature: str) -> Tuple[str, ...]:
    groups = {"calls":
                 {"dict": ("dict.clear", "dict.fromkeys", "dict.items",
                           "dict.pop", "dict.setdefault", "dict.values",
                           "dict.copy", "dict.get", "dict.keys",
                           "dict.popitem", "dict.update"),
                  "list": ("list.append", "list.clear", "list.copy",
                           "list.count", "list.extend", "list.index",
                           "list.insert", "list.pop", "list.remove",
                           "list.reverse", "list.sort"),
                  "set": ("set.add", "set.difference_update", "set.isdisjoint",
                          "set.remove", "set.update", "set.clear",
                          "set.discard", "set.issubset",
                          "set.symmetric_difference", "set.copy",
                          "set.intersection", "set.issuperset",
                          "set.symmetric_difference_update", "set.difference",
                          "set.intersection_update", "set.pop", "set.union"),
                  "str": ("str.capitalize", "str.endswith", "str.index",
                          "str.isidentifier", "str.istitle", "str.lstrip",
                          "str.rindex", "str.split", "str.title",
                          "str.casefold", "str.expandtabs", "str.isalnum",
                          "str.islower", "str.isupper", "str.maketrans",
                          "str.rjust", "str.splitlines", "str.translate",
                          "str.center", "str.find", "str.isalpha",
                          "str.isnumeric", "str.join", "str.partition",
                          "str.rpartition", "str.startswith", "str.upper",
                          "str.count", "str.format", "str.isdecimal",
                          "str.isprintable", "str.ljust", "str.replace",
                          "str.rsplit", "str.strip", "str.zfill", "str.encode",
                          "str.format_map", "str.isdigit", "str.isspace",
                          "str.lower", "str.rfind", "str.rstrip",
                          "str.swapcase"),
                  "tuple": ("tuple.count", "tuple.index")},
              "operators":
                 {"math": ("+", "-", "*", "**", "/", "//", "%"),
                  "comp": ("==", "!=", "<", ">", "<=", ">=", "is"),
                  "bool": ("not", "and", "or"),
                  "bits": ("~", "&", "|", "^")}}
    if category in groups and feature in groups[category]:
        return groups[category][feature]
    return (feature,)


def _get_range(config: configparser.ConfigParser, category: str,
               feature: str) -> Iterable[int]:
    count = config.get(category, feature, fallback="")
    if not count:
        return range(-sys.maxsize, sys.maxsize)
    if re.match(r"\d+\+", count):
        return range(int(count), sys.maxsize)
    elif re.match(r"\d+\,\d+", count):
        min_count, max_count = count.split(",")
        return range(int(min_count), int(max_count) + 1)
    elif re.match(r"\d+", count):
        return range(int(count), int(count) + 1)
    else:
        raise ValueError("Invalid range")


def _get_user_modules(paths: Tuple[str, ...]) -> Tuple[str, ...]:
    return tuple(os.path.splitext(os.path.basename(path))[0] for path in paths)


def _get_annotations(type_names: Tuple[str, ...]) -> Tuple[str, ...]:
    ann_map = {"dict": "Dict", "frozenset": "FrozenSet", "list": "List",
               "tuple": "Tuple", "set": "Set"}
    return ("typing." + ann_map[type_name] for type_name in type_names
            if type_name in ann_map)
