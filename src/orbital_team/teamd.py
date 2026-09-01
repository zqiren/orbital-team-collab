"""teamd — the file-event daemon that turns member reports into Manager runs.

teamd keeps no hidden business state: jobs, runs, results, and events all live
in the file runtime. The consumer cursor under ``consumers/teamd.json`` is a
rebuildable projection; every tick also reconciles directly from Submitted
tasks/reports and Job state, so deleting the cursor or crashing mid-run never
loses or duplicates work.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from .constants import SCHEMA_VERSION
from .errors import TeamRuntimeError
from .manager_integration import (
    DEFAULT_MAX_ATTEMPTS,
    ManagerIntegrationWorkflow,
)
from .manager_runner import (
    CommandManagerRunner,
    DEFAULT_RUN_TIMEOUT,
    ManagerRunner,
    RunContext,
    RunnerSupervisor,
)
from .storage import RuntimeLock, atomic_write_json, read_json

RETRY_EXHAUSTED_QUESTION = (
    "Integration runs for job {job_id} failed {attempts} times; "
    "how should this report proceed?"
)


class TeamDaemon:
    def __init__(
        self,
        workspace: str | os.PathLike[str],
        *,
        runners: Mapping[str, ManagerRunner] | None = None,
        manifest_dirs: list[Path] | None = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        runner_timeout: int = DEFAULT_RUN_TIMEOUT,
        validation_argv: list[str] | None = None,
    ) -> None:
        self.workflow = ManagerIntegrationWorkflow(workspace)
        self.supervisor = RunnerSupervisor(self.workflow)
        self.runners = dict(runners or {})
        self.manifest_dirs = list(manifest_dirs or [])
        self.max_attempts = max_attempts
        self.runner_timeout = runner_timeout
        self.validation_argv = validation_argv

    # ------------------------------------------------------------------
    # cursor (projection only)
    # ------------------------------------------------------------------

    @property
    def _cursor_path(self) -> Path:
        return self.workflow.runtime_root / "consumers" / "teamd.json"

    def read_cursor(self) -> int:
        if not self._cursor_path.is_file():
            return 0
        try:
            value = read_json(self._cursor_path)
        except TeamRuntimeError:
            return 0
        offset = value.get("processed_events", 0)
        return offset if isinstance(offset, int) and offset >= 0 else 0

    def _write_cursor(self, offset: int) -> None:
        atomic_write_json(
            self._cursor_path,
            {
                "consumer": "teamd",
                "processed_events": offset,
                "schema_version": SCHEMA_VERSION,
            },
        )

    # ------------------------------------------------------------------
    # runner resolution
    # ------------------------------------------------------------------

    def resolve_runner(
        self, project: dict[str, Any]
    ) -> tuple[ManagerRunner, str] | None:
        name = project["runner"]
        if name in self.runners:
            return self.runners[name], name
        if name == "manual":
            return None
        search_dirs = [
            Path(project["canonical_workspace"]) / "demo" / "runners",
            *self.manifest_dirs,
        ]
        for directory in search_dirs:
            manifest = directory / f"{name}.json"
            if manifest.is_file():
                return CommandManagerRunner.from_manifest(manifest), name
        raise TeamRuntimeError(
            "E_RUNNER_UNAVAILABLE",
            "No runner implementation or manifest matches the project runner.",
            {"runner": name},
            retryable=True,
        )

    # ------------------------------------------------------------------
    # tick phases
    # ------------------------------------------------------------------

    def _reconcile_partial_jobs(self, summary: dict[str, int]) -> None:
        """Resume create_job transactions interrupted before Task/event persistence."""
        for job in self.workflow.jobs.list():
            queued_event = self.workflow._event(f"integration:queued:{job['id']}")
            tasks = self.workflow._store(
                job["project_slug"], "tasks.json", "taskStore"
            ).read()
            task = tasks["items"].get(job["task_id"])
            if task is None:
                continue
            if task["state"] == "submitted" or queued_event is None:
                self.workflow.create_job(job["report_id"])
                summary["reconciled"] += 1

    def _recover_running_jobs(self, summary: dict[str, int]) -> None:
        """A Running job at tick start has no live run in this process: crash recovery."""
        for observed in self.workflow.jobs.list():
            if observed["state"] != "running":
                continue
            try:
                manager_lock = RuntimeLock(
                    self.workflow.manager_lock(observed["project_slug"]), timeout=0
                )
                manager_lock.__enter__()
            except TeamRuntimeError as exc:
                if exc.code == "E_LOCK_TIMEOUT":
                    continue  # another teamd still owns this live Manager run
                raise
            try:
                job = self.workflow.jobs.read(observed["id"])
                if job["state"] != "running":
                    continue
                if job["run_id"] is not None:
                    try:
                        self.supervisor.finish_run(
                            job["project_slug"], job["run_id"], "failed"
                        )
                    except TeamRuntimeError:
                        pass
                self.workflow.mark_retryable(
                    job["id"], "teamd recovery: runner is no longer alive."
                )
                summary["recovered"] += 1
            finally:
                manager_lock.__exit__(None, None, None)

    def _apply_retry_policy(self, summary: dict[str, int]) -> None:
        for observed in self.workflow.jobs.list():
            if observed["state"] != "retryable":
                continue
            try:
                with RuntimeLock(
                    self.workflow.manager_lock(observed["project_slug"]), timeout=0
                ):
                    job = self.workflow.jobs.read(observed["id"])
                    if job["state"] != "retryable":
                        continue
                    if job["attempt"] < self.max_attempts:
                        self.workflow.requeue_job(job["id"])
                        summary["requeued"] += 1
                    else:
                        self.workflow.block_job(
                            job["id"],
                            f"Retry policy exhausted after {job['attempt']} attempts.",
                            question=RETRY_EXHAUSTED_QUESTION.format(
                                job_id=job["id"], attempts=job["attempt"]
                            ),
                            actor="system:teamd",
                        )
                        summary["blocked"] += 1
            except TeamRuntimeError as exc:
                if exc.code != "E_LOCK_TIMEOUT":
                    raise

    def _tail_report_ids(self, events: tuple[dict[str, Any], ...], offset: int) -> list[str]:
        report_ids = []
        for event in events[offset:]:
            if event["type"] == "report.submitted":
                report_id = event["data"].get("report_id")
                if isinstance(report_id, str):
                    report_ids.append(report_id)
        return report_ids

    def _admit_jobs(self, summary: dict[str, int], tail_report_ids: list[str]) -> None:
        registry = self.workflow.manager._registry()
        tail_order = {report_id: index for index, report_id in enumerate(tail_report_ids)}
        for slug in sorted(registry["projects"]):
            if self.workflow.occupying_jobs(slug):
                continue
            pending = self.workflow.pending_reports(slug)
            if not pending:
                continue
            pending.sort(
                key=lambda item: (
                    item["submitted_at"],
                    tail_order.get(item["id"], len(tail_order)),
                    item["id"],
                )
            )
            try:
                self.workflow.create_job(pending[0]["id"])
                summary["jobs_created"] += 1
            except TeamRuntimeError as exc:
                if exc.code != "E_INTEGRATION_SLOT_BUSY":
                    raise

    def _drive_queued_jobs(self, summary: dict[str, int]) -> None:
        for observed in self.workflow.jobs.list():
            if observed["state"] != "queued":
                continue
            try:
                with RuntimeLock(
                    self.workflow.manager_lock(observed["project_slug"]), timeout=0
                ):
                    job = self.workflow.jobs.read(observed["id"])
                    if job["state"] != "queued":
                        continue
                    slug = job["project_slug"]
                    project = self.workflow._project(slug)
                    try:
                        resolved = self.resolve_runner(project)
                    except TeamRuntimeError:
                        summary["runner_unavailable"] = summary.get("runner_unavailable", 0) + 1
                        continue
                    if resolved is None:
                        continue  # manual runner: a human manager drives the CLI
                    runner, runner_name = resolved
                    context = self.supervisor.prepare_run(
                        job,
                        agent_type=getattr(runner, "agent_type", runner_name),
                        timeout_seconds=self.runner_timeout,
                        validation_argv=self.validation_argv,
                    )
                    try:
                        self.workflow.start_job(job["id"], context.run_id)
                    except TeamRuntimeError as exc:
                        if exc.code in ("E_INVALID_TRANSITION", "E_INTEGRATION_SLOT_BUSY"):
                            self.supervisor.finish_run(slug, context.run_id, "cancelled")
                            continue
                        raise
                    self.supervisor.mark_running(slug, context.run_id)
                    summary["jobs_started"] += 1
                    self._execute_and_apply(slug, job["id"], runner, context, summary)
            except TeamRuntimeError as exc:
                if exc.code == "E_LOCK_TIMEOUT":
                    continue
                raise

    def _execute_and_apply(
        self,
        slug: str,
        job_id: str,
        runner: ManagerRunner,
        context: RunContext,
        summary: dict[str, int],
    ) -> None:
        run_state = "succeeded"
        failure: str | None = None
        try:
            runner.run(context.request, context.request_path)
        except TeamRuntimeError as exc:
            run_state = "timed_out" if exc.code == "E_RUNNER_TIMEOUT" else "failed"
            failure = f"{exc.code}: {exc.message}"
        except Exception as exc:  # runner bugs must not kill teamd
            run_state = "failed"
            failure = f"runner exception: {exc!r}"
        result = self.supervisor.load_result(context)
        if result is None:
            run_state = run_state if run_state != "succeeded" else "failed"
            failure = failure or "Runner produced no schema-valid result file."
        self.supervisor.finish_run(slug, context.run_id, run_state)
        if result is None:
            job = self.workflow.jobs.read(job_id)
            if job["state"] == "running":
                self.workflow.mark_retryable(job_id, failure or "invalid result")
            # The controlled merge command may have completed just before the
            # runner crashed while writing its result. Its persisted Job,
            # integration record, and event are sufficient crash evidence;
            # never try to merge that report a second time.
            summary["invalid_results"] += 1
            return
        try:
            applied = self.workflow.apply_runner_result(job_id, result)
        except TeamRuntimeError as exc:
            job = self.workflow.jobs.read(job_id)
            if job["state"] == "running":
                self.workflow.mark_retryable(
                    job_id, f"Result rejected: {exc.code}: {exc.message}"
                )
            summary["invalid_results"] += 1
            return
        summary["results_applied"] += 1
        summary[f"outcome_{applied['applied']}"] = (
            summary.get(f"outcome_{applied['applied']}", 0) + 1
        )

    def _prepare_packs(self, summary: dict[str, int]) -> None:
        for job in self.workflow.jobs.list():
            if job["state"] == "merged":
                self.workflow.prepare_knowledge_pack(job["id"])
                summary["packs_prepared"] += 1

    # ------------------------------------------------------------------
    # public loop
    # ------------------------------------------------------------------

    def tick(self) -> dict[str, int]:
        summary: dict[str, int] = {
            "blocked": 0,
            "invalid_results": 0,
            "jobs_created": 0,
            "jobs_started": 0,
            "packs_prepared": 0,
            "reconciled": 0,
            "recovered": 0,
            "requeued": 0,
            "results_applied": 0,
        }
        events = self.workflow.events.read().events
        offset = min(self.read_cursor(), len(events))
        tail_report_ids = self._tail_report_ids(events, offset)
        self._reconcile_partial_jobs(summary)
        self._recover_running_jobs(summary)
        self._apply_retry_policy(summary)
        self._admit_jobs(summary, tail_report_ids)
        self._drive_queued_jobs(summary)
        self._prepare_packs(summary)
        self._write_cursor(len(events))
        return summary

    @staticmethod
    def _progress(summary: dict[str, int]) -> int:
        return sum(
            summary.get(key, 0)
            for key in (
                "blocked",
                "jobs_created",
                "jobs_started",
                "packs_prepared",
                "reconciled",
                "recovered",
                "requeued",
                "results_applied",
            )
        )

    def run_once(self, *, max_passes: int = 25) -> dict[str, int]:
        """Drain: keep ticking until a full pass makes no progress."""
        total: dict[str, int] = {}
        for _ in range(max_passes):
            summary = self.tick()
            for key, value in summary.items():
                if isinstance(value, int):
                    total[key] = total.get(key, 0) + value
            if self._progress(summary) == 0:
                break
        return total

    def run_forever(
        self,
        *,
        interval: float = 2.0,
        max_ticks: int | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        ticks = 0
        while max_ticks is None or ticks < max_ticks:
            self.run_once()
            ticks += 1
            if max_ticks is not None and ticks >= max_ticks:
                break
            sleep(interval)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="teamd")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--once", action="store_true", help="drain and exit")
    parser.add_argument("--watch", action="store_true", help="poll continuously")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--max-ticks", type=int)
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    parser.add_argument("--runner-timeout", type=int, default=DEFAULT_RUN_TIMEOUT)
    parser.add_argument(
        "--manifest-dir", action="append", default=[], help="extra runner manifest dirs"
    )
    arguments = parser.parse_args(argv)
    if arguments.once == arguments.watch:
        parser.error("choose exactly one of --once or --watch")
    try:
        daemon = TeamDaemon(
            arguments.workspace,
            manifest_dirs=[Path(item) for item in arguments.manifest_dir],
            max_attempts=arguments.max_attempts,
            runner_timeout=arguments.runner_timeout,
        )
        if arguments.once:
            summary = daemon.run_once()
            print(json.dumps(summary, sort_keys=True))
        else:
            daemon.run_forever(
                interval=arguments.interval, max_ticks=arguments.max_ticks
            )
        return 0
    except TeamRuntimeError as exc:
        print(json.dumps(exc.response(), sort_keys=True), file=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
