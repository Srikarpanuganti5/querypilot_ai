"""Readiness, reviewed gate and CI policy tests; no container-runtime claim."""

import copy
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from fastapi.testclient import TestClient
from scripts.check_ci_results import check
from scripts.prepare_docker import prepare

from querypilot.core.config import Settings
from querypilot.db.bootstrap import bootstrap
from querypilot.evaluation.gate import Baseline, compare
from querypilot.main import create_app


def reference():
    return Baseline(
        dataset_version="unit-v1",
        dataset_sha256="a" * 64,
        corpus_sha256="b" * 64,
        fixture_sha256="c" * 64,
        reference_date="2026-10-27",
        random_seed=42,
        source_commit="reviewed",
        passing_cases=["protected"],
        failing_cases=["known-failure"],
    )


def result():
    baseline = reference()
    return dict(
        dataset_version=baseline.dataset_version,
        dataset_sha256=baseline.dataset_sha256,
        corpus_sha256=baseline.corpus_sha256,
        mode="MOCK PROVIDER + REAL DATABASE",
        fixture=dict(
            sha256=baseline.fixture_sha256,
            reference_date=baseline.reference_date,
            random_seed=42,
            status="REAL DATABASE VERIFIED",
        ),
        cases=[
            dict(id="protected", score=dict(passed=True)),
            dict(id="known-failure", score=dict(passed=False)),
        ],
    )


def test_gate_accepts_known_failures_and_improvements():
    verdict = compare(result(), reference())
    assert verdict["passed"] and verdict["known_failures"] == ["known-failure"]
    better = result()
    better["cases"][1]["score"]["passed"] = True
    assert compare(better, reference())["improvements"] == ["known-failure"]


def test_gate_catches_case_swap_despite_unchanged_aggregate():
    report = result()
    report["cases"][0]["score"]["passed"] = False
    report["cases"][1]["score"]["passed"] = True
    verdict = compare(report, reference())
    assert not verdict["passed"] and verdict["regressions"] == ["protected"]


@pytest.mark.parametrize(
    "mutation", ["dataset", "corpus", "fixture", "date", "seed", "mode", "missing", "duplicate"]
)
def test_gate_rejects_incompatible_or_incomplete_reports(mutation):
    report = result()
    if mutation in {"dataset", "corpus"}:
        report[mutation + "_sha256"] = "d" * 64
    elif mutation == "fixture":
        report["fixture"]["sha256"] = "d" * 64
    elif mutation == "date":
        report["fixture"]["reference_date"] = "2026-01-01"
    elif mutation == "seed":
        report["fixture"]["random_seed"] = 7
    elif mutation == "mode":
        report["mode"] = "FULLY MOCKED"
    elif mutation == "missing":
        report["cases"].pop()
    else:
        report["cases"].append(copy.deepcopy(report["cases"][0]))
    with pytest.raises(ValueError):
        compare(report, reference())


def write_xml(path, nodes):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite")
    for node in nodes:
        module, name = node.split("::", 1)
        ET.SubElement(suite, "testcase", classname=module[:-3].replace("/", "."), name=name)
    ET.ElementTree(root).write(path)
    return root


def test_ci_requires_all_original_postgres_cases_without_skips(tmp_path):
    nodes = json.loads(Path("data/evaluations/postgres_required.json").read_text())
    path = tmp_path / "results.xml"
    write_xml(path, nodes)
    assert check(path)["postgres_passed"] == 50
    root = write_xml(path, nodes)
    ET.SubElement(next(root.iter("testcase")), "skipped")
    ET.ElementTree(root).write(path)
    with pytest.raises(ValueError, match="skipped"):
        check(path)
    write_xml(path, nodes[:-1] + ["tests/test_real_workflows.py::different_test"])
    with pytest.raises(ValueError, match="required"):
        check(path)
    write_xml(path, nodes[:-1])
    with pytest.raises(ValueError, match="Too few"):
        check(path)


def test_private_docker_settings_are_created_once_and_preserved(tmp_path):
    path = tmp_path / ".env.docker"
    assert prepare(path)
    content = path.read_text()
    assert path.stat().st_mode & 0o777 == 0o600
    assert "QP_READER_PASSWORD=" in content
    assert not prepare(path) and path.read_text() == content


def test_missing_reader_is_not_ready_but_process_is_alive():
    settings = Settings(_env_file=None, database_url=None, reader_database_url=None)
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/ready")
    assert response.status_code == 503 and response.json()["status"] == "not_ready"
    assert any(c["code"] == "reader_configuration_missing" for c in response.json()["checks"])
    assert "postgresql" not in response.text


def test_bootstrap_refuses_implicit_setup_before_connecting():
    with pytest.raises(ValueError, match="acknowledgement"):
        bootstrap(Settings(_env_file=None, database_url=None), acknowledged=False)
