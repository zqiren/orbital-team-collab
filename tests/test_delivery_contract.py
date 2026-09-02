from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

from orbital_team.cli import _parser as build_parser
from scripts.verify_clean_copy import copy_clean_source


REPO_ROOT = Path(__file__).resolve().parents[1]


class DeliveryContractTests(unittest.TestCase):
    def test_readme_reviewer_journey_commands_and_links(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for required in (
            "主要产物",
            "DESIGN.html",
            "它解决什么问题",
            "插件 + 钩子 + 本地 server",
            "怎么用",
            "两层文件模型",
            "python3 -m pip install -e .",
            "python3 -m pytest -q",
            "team_demo.py setup",
            "teamctl dashboard",
            "simulated-replay",
            "文档导航",
            "已知限制",
        ):
            self.assertIn(required, readme)
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", readme):
            if target.startswith(("http://", "https://")):
                continue
            self.assertTrue((REPO_ROOT / target).exists(), target)

    def test_all_specs_are_done_with_completion_records(self) -> None:
        index = (REPO_ROOT / "specs/README.md").read_text(encoding="utf-8")
        rows = [line for line in index.splitlines() if line.startswith("| [SPEC-")]
        self.assertEqual(10, len(rows))
        self.assertTrue(all("| Done |" in row for row in rows))
        for spec in sorted((REPO_ROOT / "specs").glob("SPEC-*.md")):
            value = spec.read_text(encoding="utf-8")
            self.assertIn("status: Done", value, spec.name)
            self.assertIn("## Completion Record", value, spec.name)
            self.assertIn("- Final status: Done", value, spec.name)

    def test_ignore_and_delivery_tree_exclude_runtime_and_build_artifacts(self) -> None:
        ignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in (
            ".venv/",
            ".pytest_cache/",
            "*.egg-info/",
            "build/",
            "dist/",
            "orbital/sessions/",
            "orbital/ledger/",
            "orbital/tool-results/",
            "orbital/queue.json",
        ):
            self.assertIn(pattern, ignore)
        with tempfile.TemporaryDirectory(prefix="delivery-copy-contract-") as temporary:
            copied = Path(temporary) / "repo"
            copy_clean_source(REPO_ROOT, copied)
            for forbidden in (
                ".git",
                ".pytest_cache",
                "orbital-src",
                "orbital/sessions",
                "orbital/ledger",
                "orbital/tool-results",
                "orbital/queue.json",
                "orbital/approval_history.jsonl",
            ):
                self.assertFalse((copied / forbidden).exists(), forbidden)

    def test_delivery_files_have_no_user_path_or_secret_pattern(self) -> None:
        forbidden_paths = (
            REPO_ROOT / "orbital-src",
            REPO_ROOT / "orbital/sessions",
            REPO_ROOT / "orbital/ledger",
            REPO_ROOT / "orbital/tool-results",
            REPO_ROOT / "orbital/output",
        )
        patterns = (
            re.compile("/" + r"Users/[^/<\s]+/"),
            re.compile("/" + r"home/[^/<\s]+/"),
            re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
            re.compile(r"AKIA[0-9A-Z]{16}"),
            re.compile(r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"),
            re.compile(r"(?:ANTHROPIC|OPENAI|MOONSHOT)_API_KEY\s*="),
        )
        for directory, dirnames, filenames in os.walk(REPO_ROOT):
            current = Path(directory)
            if current == REPO_ROOT / ".git" or any(root == current or root in current.parents for root in forbidden_paths):
                dirnames[:] = []
                continue
            dirnames[:] = [name for name in dirnames if name not in {".git", ".venv", ".pytest_cache", "__pycache__"}]
            for filename in filenames:
                if filename.endswith((".pyc", ".pyo")):
                    continue
                file_path = current / filename
                relative = file_path.relative_to(REPO_ROOT)
                if (
                    relative.as_posix() in {"orbital/queue.json", "orbital/approval_history.jsonl"}
                    or (
                        # machine-managed dispatch runtime; only MEMORY.md is a delivery file
                        relative.parts[:2] == ("orbital", "sub_agents")
                        and filename != "MEMORY.md"
                    )
                ):
                    continue
                try:
                    text = file_path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                for pattern in patterns:
                    self.assertIsNone(pattern.search(text), f"{file_path}: {pattern.pattern}")

    def test_cli_surface_matches_documented_commands(self) -> None:
        parser = build_parser()
        subparsers = next(
            action for action in parser._actions if hasattr(action, "choices") and action.choices
        )
        self.assertTrue(
            {"init", "status", "reset", "dashboard", "member", "claim", "task", "report", "context", "potential", "question", "manager"}.issubset(
                subparsers.choices
            )
        )


if __name__ == "__main__":
    unittest.main()
