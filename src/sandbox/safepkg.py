import os
import unittest
from typing import Dict, List, Tuple

from src import error
from src.rules import langfeat
from src.rules import valid
from src.sandbox import safedef
from src.sandbox import safemod
from src.sandbox import sandbox
from src.sandbox.ctxman import monitor
from src.sandbox.ctxman import timer


class TraceTestResult(unittest.TextTestResult):

    def __init__(self, *args, **kwargs) -> None:
        self.tracebacks = []
        super().__init__(*args, **kwargs)

    def addError(self, test: unittest.TestCase,
                 exc_info: error.ExcInfo) -> None:
        if not isinstance(exc_info[1], error.ReturnValueIgnoredError):
            self.tracebacks.append(exc_info)
            super().addError(test, exc_info)

    def addFailure(self, test: unittest.TestCase,
                   exc_info: error.ExcInfo) -> None:
        if not isinstance(exc_info[1], error.ReturnValueIgnoredError):

            # TODO: catch AssertionErrors for ErrorFormatter
            #       find out why AssertionErrors reported for successful cases
            if not isinstance(exc_info[1], AssertionError):
                self.tracebacks.append(exc_info)

            super().addFailure(test, exc_info)




class SafePackage(object):

    def __init__(self, course: str, assignment: str, files: Dict[str, str],
                 min_tests: int, feat_rules: langfeat.FeatRules,
                 skip_lint: bool = False, skip_type: bool = False) -> None:
        # TODO: refactor: add sandbox.update_calls method
        #       change ctxmans into dict and update CallGuard
        self.safemods: List[safemod.SafeModule] = \
            [safemod.SafeModule(path, source) for path, source in files.items()]
        feat_rules = self._update_userdef_calls(feat_rules, self.safemods)
        self.sandbox: sandbox.Sandbox = self._create_sandbox(tuple(files),
                                                             feat_rules)
        self.errors: error.ErrorFormatter = \
            valid.validate_package(course, assignment, files, feat_rules,
                                   self.safemods, skip_lint, skip_type)
        self._load_modules(min_tests)

    def _update_userdef_calls(self, feat_rules: langfeat.FeatRules,
                              safemods: List[safemod.SafeModule]
    ) -> langfeat.FeatRules:
        defs = [def_name for sm in safemods for def_name in sm.nodes]
        for def_name in defs:
            if def_name.endswith(".__init__"):
                defs.append(def_name.rsplit(".", maxsplit=1)[0])
        return langfeat.update_features(feat_rules, "calls", tuple(defs))

    def __getattr__(self, name: str) -> safemod.SafeModule:
        for sm in self.safemods:
            if sm.name == name:
                return sm
        raise ModuleNotFoundError(name)

    def __getitem__(self, key: str) -> safemod.SafeModule:
        return getattr(self, key)

    def is_loaded(self) -> bool:
        return all(sm.module is not None for sm in self.safemods)

    def _create_sandbox(self, paths: List[str],
                        feat_rules: langfeat.FeatRules,
                        keep_prompt: bool = False) -> sandbox.Sandbox:
        calls = tuple(feat_rules["calls"])
        imports = tuple(feat_rules["imports"])
        dirname = os.path.dirname(paths[0])
        return sandbox.Sandbox(calls, imports, dirname, keep_prompt)

    def _load_modules(self, min_tests: int) -> None:
        """
        Load the module associated with each SafeModule object in
        |self.safemods|. Return True if all modules were loaded and False if at
        least one module was not loaded due to an error.

        Modules that are not test suites are loaded first as they may all need
        to be loaded to run any test suites.
        """
        self._load_definitions()
        if self._has_unittests():
            self._load_unittests(min_tests)

    def _load_definitions(self) -> None:
        for sm in self.safemods:
            if not sm.is_suite and sm.name not in self.errors:
                sm.load(self.errors, self.sandbox)

    def _has_unittests(self) -> bool:
        return any(sm.is_suite for sm in self.safemods)

    def _load_unittests(self, min_tests: int) -> None:
        with monitor.CallMonitor(self.safemods) as cm:
            for sm in self.safemods:
                if sm.is_suite and sm.name not in self.errors:
                    if sm.load(self.errors, self.sandbox):
                        for exc_info in self._run_unittests(sm):
                            self.errors.add_traceback(sm.name, exc_info)
        for sm in self.safemods:
            if not sm.is_suite and sm.module:
                insufficient = cm.validate_calls(sm, min_tests)
                self._disable_untested(insufficient)
#            report = cm.get_analysis()

    def _disable_untested(self, insufficient: List[Tuple[str, str]]) -> None:
        for name, message in insufficient:
            try:
                mod_name, def_name = name.split(".")
            except ValueError:  # module.class.function
                pass  # TODO: implement method call validation
                      #       presently ignores class methods (e.g. ListNode)
            else:
                self.errors.add(name, message, hidden=False)
                self[mod_name][def_name].disable_function()

    def _run_unittests(self, sm: safemod.SafeModule,
                       seconds: int = 5) -> List[str]:
        tb_list = []
        was_successful = True
        with open(os.devnull, "w") as devnull:
            driver = unittest.TextTestRunner(stream=devnull, verbosity=0,
                                             resultclass=TraceTestResult)
            load_tests = unittest.defaultTestLoader.loadTestsFromModule
            for tests in load_tests(sm.module):
                # TODO: mark test as failure if time limit exceeded
                with timer.Timer(seconds):
                    result = driver.run(tests)
                if not result.wasSuccessful():
                    was_succesful = False
                    for exc_info in result.tracebacks:
                        tb_list.append(exc_info)
#        if tb_list:
        if not was_successful:
            sm.module = None  # TODO: do proper unload?
        return tb_list
