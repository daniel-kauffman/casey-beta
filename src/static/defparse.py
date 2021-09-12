import ast
from typing import Dict, List, Set


def parse_exceptions(root: ast.FunctionDef) -> Dict[str, Set[int]]:
    """
    Return a mapping of exception names to the line numbers where those
    exceptions were used.
    """
    exceptions = {}
    allowed = ("AssertionError", "AttributeError", "EOFError", "IndexError",
               "KeyError", "RuntimeError", "TypeError", "ValueError",
               "ZeroDivisionError")
    for node in ast.walk(root):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                exceptions.setdefault("BaseException", set()).add(node.lineno)
            elif hasattr(node.type, "elts"):
                for elt in node.type.elts:
                    if elt.id not in allowed:
                        exceptions.setdefault(elt.id, set()).add(node.lineno)
            elif hasattr(node.type, "id") and node.type.id not in allowed:
                exceptions.setdefault(node.type.id, set()).add(node.lineno)
        elif isinstance(node, ast.Raise):
            if isinstance(node.exc, ast.Call):
                # TODO: support node.func.attr
                name = node.exc.func.id + "(...)"
                exceptions.setdefault(name, set()).add(node.lineno)
            elif hasattr(node, "id") and node.id not in allowed:
                exceptions.setdefault(node.id, set()).add(node.lineno)
    return exceptions


def parse_calls(root: ast.FunctionDef) -> Dict[str, Set[int]]:
    """
    Return a mapping of function names to the line numbers where those
    functions were called.
    """
    calls = {}
    for node in ast.walk(root):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):  # built-in functions
                calls.setdefault(node.func.id, set()).add(node.lineno)

    # TODO: detect type of calling object for method calls
#            elif isinstance(node.func, ast.Attribute):
#                calling_obj = getattr(node.func.value, "id", "") 
#                if calling_obj != "self":
#                    method_name = calling_obj + "." + node.func.attr
#                    calls.setdefault(method_name, set()).add(node.lineno)

    return calls


def parse_keywords(root: ast.FunctionDef) -> Dict[str, Set[int]]:
    """
    Return a mapping of Python keyword names to the line numbers where those
    keywords were used. Ignore the occurrence of |def| on the first line of the
    function, but not when used for nested functions.
    """
    keywords = {}
    for node in ast.walk(root):
        keyword = _get_keyword(node)
        if keyword and (keyword != "def" or node.lineno > root.lineno):
            keywords.setdefault(keyword, set()).add(node.lineno)
    return keywords


def _get_keyword(node: ast.AST) -> str:
    """
    Given an AST node, return a string representing the keyword with which it
    corresponds, or an empty string otherwise.
    """
    kw_map = {  "assert": (ast.Assert,),
                 "break": (ast.Break,),
                 "class": (ast.ClassDef,),
              "continue": (ast.Continue,),
                   "def": (ast.FunctionDef, ast.AsyncFunctionDef),
                   "del": (ast.Delete,),
                   "for": (ast.For, ast.AsyncFor),
                "global": (ast.Global,),
                    "if": (ast.If,),
                "import": (ast.Import, ast.ImportFrom),
                "lambda": (ast.Lambda,),
              "nonlocal": (ast.Nonlocal,),
                 "raise": (ast.Raise,),
                "return": (ast.Return,),
                   "try": (ast.Try,),
                 "while": (ast.While,),
                  "with": (ast.With, ast.AsyncWith),
                 "yield": (ast.Yield, ast.YieldFrom)}
    for key, cls_list in kw_map.items():
        if isinstance(node, cls_list):
            return key
    return ""


def parse_operators(root: ast.FunctionDef) -> Dict[str, Set[int]]:
    """
    Return a mapping of Python operators to the line numbers where those
    operators were used, which includes arithmetic, relational, Boolean, and
    bitwise operators.

    Additional operators are given the following names:

           Operator   |     Example    | Name Given
        --------------------------------------------
           Assignment | xs = []        | "store"
             Indexing | xs[0]          | "index"
              Slicing | xs[1:]         | "slice"
        If-Expression | 1 if xs else 0 | "ifexp"
    """
    operators = {}
    for node in ast.walk(root):
        if isinstance(node, ast.IfExp):
            operators.setdefault("ifexp", set()).add(node.lineno)
        elif isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Index):
                operators.setdefault("index", set()).add(node.lineno)
            elif isinstance(node.slice, (ast.Slice, ast.ExtSlice)):
                operators.setdefault("slice", set()).add(node.lineno)
        elif isinstance(node, ast.Compare):
            for node_op in node.ops:
                op = _get_op(node_op)
                if op:
                    operators.setdefault(op, set()).add(node.lineno)
                    if isinstance(node_op, (ast.Not, ast.IsNot, ast.NotIn)):
                        operators.setdefault("not", set()).add(node.lineno)
        elif isinstance(node, (ast.UnaryOp, ast.BinOp, ast.BoolOp,
                               ast.AugAssign)):
            op = _get_op(node.op)
            if op:
                operators.setdefault(op, set()).add(node.lineno)
        elif isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            operators.setdefault("store", set()).add(node.lineno)
    return operators


def _get_op(node: ast.AST) -> str:
    """
    Given an AST node, return a string representing the operator with which it
    corresponds, or an empty string otherwise.
    """
    op_map = {  "+": (ast.UAdd, ast.Add),
                "-": (ast.USub, ast.Sub),
                "*": (ast.Mult,),
               "**": (ast.Pow,),
                "/": (ast.Div,),
               "//": (ast.FloorDiv,),
                "%": (ast.Mod,),
               "==": (ast.Eq,),
               "!=": (ast.NotEq,),
                "<": (ast.Lt,),
                ">": (ast.Gt,),
               "<=": (ast.LtE,),
               ">=": (ast.GtE,),
              "and": (ast.And,),
               "or": (ast.Or,),
               "in": (ast.In, ast.NotIn),
               "is": (ast.Is, ast.IsNot),
                "~": (ast.Invert,),
                "&": (ast.BitAnd,),
                "|": (ast.BitOr,),
                "^": (ast.BitXor,),
               "<<": (ast.LShift,),
               ">>": (ast.RShift,)}
    for key, cls_list in op_map.items():
        if isinstance(node, cls_list):
            return key
    return ""


def parse_types(root: ast.FunctionDef) -> Dict[str, Set[int]]:
    """
    Return a mapping of Python built-in data types to the line numbers where
    those types were used, which includes the use of built-in casting functions.
    """
    # TODO: use more robust method of ignoring types in test case functions
    if root.name.startswith("test_"):
        return {}

    data_types = {}
    for node in ast.walk(root):
        if isinstance(node, ast.NameConstant):
            if node.value is not None:
                data_types.setdefault("bool", set()).add(node.lineno)
            else:
                data_types.setdefault("NoneType", set()).add(node.lineno)
        elif isinstance(node, ast.Num):
            type_name = type(node.n).__name__
            data_types.setdefault(type_name, set()).add(node.lineno)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("bool", "bytes", "dict", "float", "int",
                                "list", "set", "str", "tuple"):
                data_types.setdefault(node.func.id, set()).add(node.lineno)
        else:
            type_name = _get_type(node)
            if type_name:
                data_types.setdefault(type_name, set()).add(node.lineno)
    return data_types


def _get_type(node: ast.AST) -> str:
    type_map = {"bytes": (ast.Bytes,),
                 "dict": (ast.Dict, ast.DictComp),
                 "list": (ast.List, ast.ListComp),
                  "set": (ast.Set, ast.SetComp),
                  "str": (ast.Str,),
                "tuple": (ast.Tuple, ast.GeneratorExp)}
    for key, cls_list in type_map.items():
        if isinstance(node, cls_list):
            return key
    return ""


#def _is_base_exception(name: str) -> bool:
#    """
#    Return True if the given exception name refers to a base exception and False
#    otherwise. For this function, a base exception is one that inherits from the
#    BaseException class but is not a descendant of the Exception class.
#    """
#    try:
#        obj = eval(name)
#    except NameError:
#        return False  # not builtin
#    else:
#        return (isinstance(obj, type) and issubclass(obj, BaseException)
#                and (obj == Exception or not issubclass(obj, Exception)))
