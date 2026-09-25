"""Job registry. Other modules add jobs with ``@job(...)``."""

from __future__ import annotations

import importlib
import logging
import traceback
from collections.abc import Callable, Sequence
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Job:
    name: str
    description: str
    fn: Callable[[], str]


@dataclass(frozen=True)
class JobResult:
    name: str
    ok: bool
    summary: str


JOBS: dict[str, Job] = {}
DAILY: list[str] = []

# Modules whose import registers jobs. Kept explicit so the order is predictable.
JOB_MODULES: list[str] = ["gauge.sources.jobs", "gauge.jobs.core"]


def job(name: str, description: str, *, daily: bool = False):
    def register(fn: Callable[[], str]) -> Callable[[], str]:
        JOBS[name] = Job(name, description, fn)
        if daily and name not in DAILY:
            DAILY.append(name)
        return fn

    return register


def load_job_modules() -> None:
    for module in JOB_MODULES:
        importlib.import_module(module)


def run_jobs(names: Sequence[str]) -> list[JobResult]:
    results = []
    for name in names:
        try:
            results.append(JobResult(name, True, JOBS[name].fn()))
        except Exception as exc:  # a failing job must not stop the others
            log.error("job %s failed:\n%s", name, traceback.format_exc())
            results.append(JobResult(name, False, f"{type(exc).__name__}: {exc}"))
    return results


@job("noop", "Check that the job runner works.")
def _noop() -> str:
    return "job runner is working"
