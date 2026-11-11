"""Fail CI on skipped tests or fewer than the existing 50 executed PostgreSQL cases."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def check(path: Path, minimum_postgres: int = 50) -> dict:
    cases = list(ET.parse(path).getroot().iter("testcase"))
    postgres = [
        c
        for c in cases
        if c.attrib.get("classname", "").split(".")[-1]
        in {
            "test_database_postgres",
            "test_tools_postgres",
            "test_real_workflows",
            "test_evaluation_postgres",
            "test_deployment_postgres",
        }
    ]
    if not cases or any(
        c.find("skipped") is not None
        or c.find("failure") is not None
        or c.find("error") is not None
        for c in cases
    ):
        raise ValueError("Missing, failed or skipped tests; CI must execute every required test")
    if len(postgres) < minimum_postgres:
        raise ValueError("Too few real PostgreSQL tests executed")
    required = set(json.loads(Path("data/evaluations/postgres_required.json").read_text()))
    executed = {
        c.attrib.get("classname", "").replace(".", "/") + ".py::" + c.attrib["name"]
        for c in postgres
    }
    if not required <= executed:
        raise ValueError("One or more required Day 11 PostgreSQL cases were not executed")
    return {"passed": len(cases), "postgres_passed": len(postgres), "skipped": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    print(check(args.report))
