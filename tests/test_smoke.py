"""Verify the installed src-layout package can be imported."""

import querypilot


def test_package_import() -> None:
    assert querypilot.__name__ == "querypilot"
