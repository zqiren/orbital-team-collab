"""Sandbox-safe pytest collection.

In restricted environments (e.g. macOS seatbelt sandboxes) pytest's directory
collection stats the rootdir's *parent* (Session._collect_path ->
gethookproxy(rootpath.parent) -> Conftest lookup -> path.is_file()), which is
unreadable there and raises PermissionError during collection. Treat unreadable
paths as conftest-free directories. On normal machines the except branch never
triggers and this module is a no-op.
"""

from _pytest.config import PytestPluginManager

_original_getconftestmodules = PytestPluginManager._getconftestmodules


def _sandbox_safe_getconftestmodules(self, path):
    try:
        return _original_getconftestmodules(self, path)
    except PermissionError:
        return ()  # unreadable ancestor directory: no conftests can apply there


PytestPluginManager._getconftestmodules = _sandbox_safe_getconftestmodules
