import ast
import re
from typing import Dict, Set

# TODO: parse class defs for non-def statements


def parse_header(source: str) -> Set[int]:
    linenos = set()
    source_lines = source.splitlines()
    pattern = re.compile(r"^\s*(#.*)?$")
    for i, line in enumerate(source_lines):
        if not re.match(pattern, line):
            break
        if line.strip():
            linenos.add(i + 1)
    return linenos


def parse_imports(root: ast.AST) -> Dict[str, Set[int]]:
    imports = {}
    for node in ast.iter_child_nodes(root):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                key = alias.name
                if isinstance(node, ast.ImportFrom):
                    key = node.module + "." + key
                if alias.asname:
                    key += ":" + alias.asname
                imports.setdefault(key, set()).add(node.lineno)
    return imports


def parse_globals(root: ast.AST) -> Set[int]:
    linenos = set()
    allowed = (ast.ClassDef, ast.FunctionDef, ast.Import, ast.ImportFrom)
    for node in ast.iter_child_nodes(root):
        if not isinstance(node, allowed):
            if not isinstance(node, ast.If) or not _is_main_condition(node):
                linenos.add(node.lineno)
    return linenos


def _is_main_condition(node: ast.If) -> bool:
    if not isinstance(node.test, ast.Compare):
        return False
    elif len(node.test.ops) != 1:
        return False
    elif not isinstance(node.test.ops[0], ast.Eq):
        return False
    elif node.test.left.id != "__name__":
        return False
    elif len(node.test.comparators) != 1:
        return False
    elif node.test.comparators[0].s != "__main__":
        return False
    elif len(node.orelse) != 0:
        return False
    for expr in node.body:
        if not isinstance(expr, ast.Expr):
            return False
        elif not isinstance(expr.value, ast.Call):
            return False
    return True
#    elif len(node.body) != 1:
#        return False
#    elif not isinstance(node.body[0], ast.Expr):
#        return False
#    elif not isinstance(node.body[0].value, ast.Call):
#        return False
#    call = node.body[0].value
#    has_args = len(call.args) > 0 or len(call.keywords) > 0
#    # TODO: support main(sys.argv)
#    if isinstance(call.func, ast.Name):
#        return call.func.id == "main" and not has_args
#    elif isinstance(call.func, ast.Attribute):
#        return (isinstance(call.func.value, ast.Name)
#                and call.func.value.id == "unittest"
#                and call.func.attr == "main"
#                and not has_args)
#    return False
