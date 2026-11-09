"""REAL DATABASE + MOCK PROVIDER; references never come from the mock's own answer."""

import asyncio
import json

import pytest

from querypilot.core.security import SecretGuard
from querypilot.evaluation.dataset import load_dataset
from querypilot.evaluation.reports import write_reports
from querypilot.evaluation.runner import run_evaluation, verify_fixture

pytestmark = pytest.mark.postgres


def test_full_benchmark_real_tools_references_repeatability_and_reports(
    integration_settings, tmp_path
):
    dataset, checksum = load_dataset()
    first = asyncio.run(run_evaluation(dataset, integration_settings, dataset_hash=checksum))
    second = asyncio.run(run_evaluation(dataset, integration_settings, dataset_hash=checksum))
    assert first["fixture"]["status"] == "REAL DATABASE VERIFIED"
    assert first["fixture"]["counts"]["orders"] == 3000
    assert first["summary"]["cases"] == len(dataset.cases)
    assert [case["score"] for case in first["cases"]] == [case["score"] for case in second["cases"]]
    assert first["corpus_sha256"] == second["corpus_sha256"]
    assert first["fixture"]["sha256"] == second["fixture"]["sha256"]
    accepted = {c["id"]: c for c in first["cases"] if c["id"].startswith("accept-")}
    assert len(accepted) == 4
    assert all(c["score"]["passed"] for c in accepted.values())
    payments = accepted["accept-failed-payments"]["score"]["facts"]
    assert payments[0]["actual"] == [486] and payments[0]["evidence_match"]
    # Known mock weaknesses must be represented, not removed or turned into test failures.
    assert any(not c["score"]["passed"] for c in first["cases"])
    assert first["summary"]["benchmark_pass_rate"]["denominator"] == len(dataset.cases)
    files = write_reports(first, tmp_path, SecretGuard(integration_settings))
    assert json.loads(files[0].read_text())["cases"] == first["cases"]
    assert "LIVE OPENAI NOT VERIFIED" in files[1].read_text()


def test_fixture_mismatch_is_rejected_without_writes(integration_settings):
    dataset, _ = load_dataset()
    altered = dataset.model_copy(update={"random_seed": 43})
    with pytest.raises(ValueError, match="differs"):
        verify_fixture(integration_settings, altered)
    # Normal fixture still verifies after the refused run; no migration/seed/reset occurred.
    assert verify_fixture(integration_settings, dataset)["counts"]["products"] == 100
