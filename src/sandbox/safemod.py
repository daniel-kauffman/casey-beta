import ast
import importlib
import inspect
import os
import re
import sys
import types
from typing import Dict, Optional, List, Tuple

from src import error
from src.rules import langfeat
from src.sandbox import safedef
from src.sandbox import sandbox
#from src.sandbox.ctxman import disable


class SafeModule(object):

    def __init__(self, path: str, source: str) -> None:
        self.path: str = path
        self.name: str = os.path.splitext(os.path.basename(self.path))[0]
        self.is_suite: bool = self.name.lower().endswith("tests")
        self.module: Optional[types.ModuleType] = None
        self.source: str = source
        self.lines: List[str] = self.source.splitlines(True)
        self.root: ast.AST = self._parse_ast(self.path, self.source)
        self.nodes: Dict[str, ast.FunctionDef] = self._get_nodes(self.root)

    def __contains__(self, item: str) -> bool:
        return self.module and item in self.module.__dict__

    # TODO: implement safecls
    def __getattr__(self, name: str) -> safedef.SafeFunction:
        name = name.replace(f"{self.name}.", "")
        if "." in name:
            cls_name, def_name = name.rsplit(".", maxsplit=1)
            return getattr(self.module.__dict__[cls_name], def_name)
        else:
            obj = self.module.__dict__.get(name)
            # TODO: remove inspect.isclass clause when methods are sandboxed
            if isinstance(obj, safedef.SafeFunction) or inspect.isclass(obj):
                return obj
        raise NotImplementedError(name)

    def __getitem__(self, key: str) -> safedef.SafeFunction:
        return getattr(self, key)

    def __setitem__(self, key: str, value) -> None:
        key = key.replace(f"{self.name}.", "")
        self.module.__dict__[key] = value

    def load(self, errors: error.ErrorFormatter, sb: sandbox.Sandbox) -> bool:
        """
        Return True if the module was successfully loaded and False otherwise.

        Side-effects: Adds any errors encountered to pkg.errors.
        """
        try:
            self.module = self._import_module(sb)
        except ModuleNotFoundError:
            pass
        except:
            errors.add_traceback(self.name, sys.exc_info())
            return False
        if self.module and not self.is_suite:
            self._wrap_functions(self.module, sb)
            for def_name in self.nodes:
                if def_name in errors:


                    # TODO: remove (method call false positive workaround)
                    keys = errors._to_print[def_name].keys()
                    if all(re.match(r"^\[call:\w+\.\w+]", k) for k in keys):
                        continue


                    try:
                        self[def_name].disable_function()
                    except AttributeError:
                        pass  # TODO: disable methods containing errors
                        # TODO: occurs when def_name is a method
                        #       sandbox method calls and remove try/except
#                        cls_name, def_name = def_name.split(".", maxsplit=1)
#                        setattr(self.module.__dict__[cls_name], def_name,
#                                safedef.SafeFunction.disable(def_name))
        return True

    # TODO: use sandbox
    def _import_module(self, sb: sandbox.Sandbox) -> types.ModuleType:
        module_name = inspect.getmodulename(self.path)
        sys.modules.pop(module_name, None)
        sys.path.insert(0, os.path.dirname(self.path))
#        with sb:
        module = importlib.import_module(module_name)
#        globals()[module_name] = module
        sys.modules[module_name] = module
        return module

    def _wrap_functions(self, module: types.ModuleType,
                        sb: sandbox.Sandbox) -> None:
        for name, function in inspect.getmembers(module, inspect.isfunction):
            module.__dict__[name] = safedef.SafeFunction(function, sb)

        for cls_name, cls in inspect.getmembers(module, inspect.isclass):
            if cls_name != "typing":

                # TODO: remove when methods are sandboxed?
                module.__dict__[cls_name] = cls

#                for name, method in inspect.getmembers(cls, inspect.isfunction):
#                    setattr(self.module.__dict__[cls_name], name,
#                            safedef.SafeFunction(method, sb))

    def _parse_ast(self, path: str, source: str) -> ast.AST:
        try:
            return ast.parse(source)
        except SyntaxError as e:
            e.filename = os.path.basename(path)
            raise e

    def _get_nodes(self, root: ast.AST,
                   cls_name: str = "") -> Dict[str, ast.FunctionDef]:
        """
        Return a mapping of function names to definition ASTs.
        """
        nodes = {}
        for node in ast.iter_child_nodes(root):
            if isinstance(node, ast.FunctionDef):
                if cls_name:
                    nodes[f"{self.name}.{cls_name}.{node.name}"] = node
                else:
                    nodes[f"{self.name}.{node.name}"] = node
            elif isinstance(node, ast.ClassDef):
                nodes.update(self._get_nodes(node, cls_name=node.name))
        return nodes
