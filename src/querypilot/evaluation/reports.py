"""Small secret-screened summaries; no prompts, credentials, arguments or raw records."""

import json
from pathlib import Path

from querypilot.core.security import SecretGuard


def markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# QueryPilot evaluation",
        "",
        f"Date: {report['created_at']}",
        f"Dataset: {report['dataset_version']} ({report['dataset_sha256']})",
        f"Mode: {report['mode']}",
        f"Fixture: {report['fixture']}",
        f"Corpus SHA256: {report['corpus_sha256']}",
        f"Configuration: {report['configuration']}",
        "",
        "Metrics include numerator/denominator or the number of averaged queries/cases.",
        "",
    ]
    for name in (
        "tool_selection",
        "retrieval",
        "citations",
        "factual_checks",
        "reliability",
        "performance",
    ):
        lines.extend(
            [
                f"## {name.replace('_', ' ').title()}",
                "",
                "```json",
                json.dumps(summary[name], indent=2),
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Categories",
            "",
            "| Category | Cases | Passed | Precision | Recall | F1 | Mean ms |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name, metrics in report["categories"].items():
        lines.append(
            f"| {name} | {metrics['cases']} | {metrics['benchmark_pass_rate']['numerator']} | "
            f"{metrics['tool_selection']['precision']['value']:.3f} | "
            f"{metrics['tool_selection']['recall']['value']:.3f} | "
            f"{metrics['tool_selection']['f1']['value']:.3f} | "
            f"{metrics['performance']['mean_ms']:.3f} |"
        )
    lines.extend(
        [
            "",
            "Detailed per-category metric denominators are in the JSON report.",
            "",
        ]
    )
    lines.extend(
        [
            "## Per-case execution",
            "",
            "| Case | Expected tools | Selected tools | Status | Verdict | Duration ms |",
            "| --- | --- | --- | --- | --- | ---: |",
        ]
    )
    for case in report["cases"]:
        lines.append(
            f"| {case['id']} | {', '.join(case['expected_tools']) or 'none'} | "
            f"{', '.join(case['selected_tools']) or 'none'} | {case['status']} | "
            f"{'PASS' if case['score']['passed'] else 'FAIL'} | {case['duration_ms']:.3f} |"
        )
    lines.append("")
    lines.extend(["## Failed cases", ""])
    for case in report["cases"]:
        if not case["score"]["passed"]:
            failed = [name for name, ok in case["score"]["checks"].items() if not ok]
            lines.append(f"- {case['id']}: {', '.join(failed)}; errors={case['error_codes']}")
    lines.extend(
        [
            "",
            "## Limits",
            "",
            *[f"- {item}" for item in report["limitations"]],
            "- LIVE OPENAI NOT VERIFIED",
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(
    report: dict, output: Path, guard: SecretGuard, format: str = "both"
) -> list[Path]:
    if format not in {"both", "json", "markdown"}:
        raise ValueError("Unknown report format")
    output.mkdir(parents=True, exist_ok=True)
    safe = guard.sanitize(report)
    files = []
    for name, content in (
        ("results.json", json.dumps(safe, indent=2, ensure_ascii=False) + "\n"),
        ("results.md", markdown(safe)),
    ):
        if (name.endswith("json") and format == "markdown") or (
            name.endswith("md") and format == "json"
        ):
            continue
        path = output / name
        if path.is_symlink():
            raise ValueError("Refusing a symlinked report file")
        path.write_text(guard.redact(content), encoding="utf-8")
        files.append(path)
    return files
