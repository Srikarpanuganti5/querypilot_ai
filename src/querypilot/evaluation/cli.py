"""Run a bounded local benchmark; live paid evaluation is deliberately unavailable."""

import argparse
import asyncio
from pathlib import Path

from querypilot.core.config import Settings
from querypilot.core.security import SecretGuard
from querypilot.evaluation.dataset import DEFAULT_DATASET, load_dataset
from querypilot.evaluation.reports import write_reports
from querypilot.evaluation.runner import run_evaluation


def main(arguments: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["mock", "live"], default="mock")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--category")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("reports/evaluation/local"))
    parser.add_argument("--format", choices=["both", "json", "markdown"], default="both")
    args = parser.parse_args(arguments)
    if args.mode == "live":
        parser.error(
            "Live evaluation is not enabled; paid usage requires a separately approved run."
        )
    try:
        dataset, checksum = load_dataset(args.dataset)
        settings = Settings()
        report = asyncio.run(
            run_evaluation(
                dataset,
                settings,
                dataset_hash=checksum,
                category=args.category,
                limit=args.limit,
                k=args.k,
            )
        )
        write_reports(report, args.output, SecretGuard(settings), args.format)
    except Exception:
        raise SystemExit(
            "Evaluation failed safely; check dataset, corpus and reader/fixture readiness. "
            "Run querypilot.cli doctor. No raw diagnostic is exposed."
        ) from None
    passed = report["summary"]["benchmark_pass_rate"]
    print(f"{report['mode']}: {passed['numerator']}/{passed['denominator']} cases passed.")
    print("JSON/Markdown reports written as requested. LIVE OPENAI NOT VERIFIED.")
    raise SystemExit(0 if passed["numerator"] == passed["denominator"] else 1)
