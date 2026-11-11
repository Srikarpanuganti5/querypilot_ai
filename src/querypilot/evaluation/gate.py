"""Reviewed case-level regression gate; never regenerates baseline from current output."""

import argparse
import asyncio
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from querypilot.core.config import Settings
from querypilot.core.security import SecretGuard
from querypilot.evaluation.dataset import load_dataset
from querypilot.evaluation.reports import write_reports
from querypilot.evaluation.runner import run_evaluation

BASELINE = Path("data/evaluations/baseline_day11.json")


class Baseline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_version: str
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    corpus_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fixture_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reference_date: str
    random_seed: int
    source_commit: str
    passing_cases: list[str]
    failing_cases: list[str]


def compare(report: dict, baseline: Baseline) -> dict:
    cases = report["cases"]
    ids = [case["id"] for case in cases]
    expected = baseline.passing_cases + baseline.failing_cases
    fixture = report["fixture"]
    if (
        len(ids) != len(set(ids))
        or len(expected) != len(set(expected))
        or set(ids) != set(expected)
        or report["dataset_version"] != baseline.dataset_version
        or report["dataset_sha256"] != baseline.dataset_sha256
        or report["corpus_sha256"] != baseline.corpus_sha256
        or fixture.get("sha256") != baseline.fixture_sha256
        or fixture.get("reference_date") != baseline.reference_date
        or fixture.get("random_seed") != baseline.random_seed
        or fixture.get("status") != "REAL DATABASE VERIFIED"
        or report["mode"] != "MOCK PROVIDER + REAL DATABASE"
    ):
        raise ValueError("Baseline identity mismatch or incomplete evaluation")
    failed = {case["id"] for case in cases if not case["score"]["passed"]}
    regressions = sorted(set(baseline.passing_cases) & failed)
    improvements = sorted(set(baseline.failing_cases) - failed)
    return {
        "passed": not regressions,
        "regressions": regressions,
        "known_failures": sorted(failed & set(baseline.failing_cases)),
        "all_current_failures": sorted(failed),
        "improvements": improvements,
        "protected_cases": len(baseline.passing_cases),
        "cases": len(ids),
    }


def main(arguments: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/evaluation/gate"))
    args = parser.parse_args(arguments)
    try:
        baseline = Baseline.model_validate_json(BASELINE.read_text())
        dataset, checksum = load_dataset()
        settings = Settings()
        report = asyncio.run(run_evaluation(dataset, settings, dataset_hash=checksum))
        verdict = compare(report, baseline)
        report["regression_gate"] = verdict
        write_reports(report, args.output, SecretGuard(settings))
        print(json.dumps(verdict))
    except Exception:
        raise SystemExit(
            "Regression gate failed safely; check baseline identity and prerequisites."
        ) from None
    raise SystemExit(0 if verdict["passed"] else 1)


if __name__ == "__main__":
    main()
