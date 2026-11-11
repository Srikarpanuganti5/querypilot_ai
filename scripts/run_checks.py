"""CI parity against an acknowledged test database; any skipped test fails the run."""

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    if (
        not os.getenv("TEST_DATABASE_URL")
        or not os.getenv("TEST_READER_DATABASE_URL")
        or os.getenv("QUERYPILOT_TEST_DATABASE_ACK") != "allow-isolated-schemas"
    ):
        raise SystemExit("Load the dedicated integration environment before running CI checks.")
    # Evaluation uses exactly the acknowledged test target, not a developer .env target.
    env = {
        **os.environ,
        "DATABASE_URL": os.environ["TEST_DATABASE_URL"],
        "READER_DATABASE_URL": os.environ["TEST_READER_DATABASE_URL"],
        "QUERYPILOT_AGENT_LIVE_ENABLED": "false",
        "OPENAI_API_KEY": "",
        "OPENAI_MODEL": "",
    }
    Path(".local").mkdir(exist_ok=True)
    commands = [
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--branch",
            "--source=src/querypilot",
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            "--junitxml=.local/ci-results.xml",
        ],
        [sys.executable, "scripts/check_ci_results.py", ".local/ci-results.xml"],
        [sys.executable, "-m", "coverage", "report"],
        [sys.executable, "-m", "coverage", "json", "-o", ".local/ci-coverage.json"],
        [sys.executable, "-m", "querypilot.cli", "doctor", "--reference-date", "2026-10-27"],
        [sys.executable, "-m", "querypilot.evaluation.gate"],
    ]
    for command in commands:
        subprocess.run(command, env=env, check=True)


if __name__ == "__main__":
    main()
