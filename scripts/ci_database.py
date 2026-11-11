"""Create one ephemeral CI-owned PostgreSQL container with random masked credentials."""

import os
import secrets
import subprocess
import time
from pathlib import Path


def main() -> None:
    if os.getenv("CI") != "true" or not os.getenv("GITHUB_ENV"):
        raise SystemExit(
            "This bootstrap is restricted to GitHub CI; use native/Compose setup locally."
        )
    setup_password, reader_password = secrets.token_hex(24), secrets.token_hex(24)
    # Workflow commands mask generated values before anything can echo them.
    for value in (setup_password, reader_password):
        print(f"::add-mask::{value}", flush=True)
    container = "querypilot-ci-" + secrets.token_hex(8)
    env = {
        **os.environ,
        "POSTGRES_USER": "querypilot_setup",
        "POSTGRES_DB": "querypilot_ci_test",
        "POSTGRES_PASSWORD": setup_password,
    }
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            container,
            "-e",
            "POSTGRES_USER",
            "-e",
            "POSTGRES_DB",
            "-e",
            "POSTGRES_PASSWORD",
            "-p",
            "127.0.0.1::5432",
            "postgres:16.13-alpine",
        ],
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
        timeout=60,
    )
    try:
        port = (
            subprocess.check_output(["docker", "port", container, "5432"], text=True, timeout=10)
            .strip()
            .rsplit(":", 1)[1]
        )
        writer = f"postgresql+psycopg://querypilot_setup:{setup_password}@127.0.0.1:{port}/querypilot_ci_test"
        reader = f"postgresql+psycopg://querypilot_reader:{reader_password}@127.0.0.1:{port}/querypilot_ci_test"
        values = dict(
            QP_CI_CONTAINER=container,
            DATABASE_URL=writer,
            READER_DATABASE_URL=reader,
            TEST_DATABASE_URL=writer,
            TEST_READER_DATABASE_URL=reader,
            QUERYPILOT_SETUP_ACK="synthetic-only",
            QUERYPILOT_TEST_DATABASE_ACK="allow-isolated-schemas",
            QUERYPILOT_AGENT_LIVE_ENABLED="false",
        )
        with Path(os.environ["GITHUB_ENV"]).open("a") as file:
            file.write("".join(f"{key}={value}\n" for key, value in values.items()))
        for _ in range(60):
            if (
                subprocess.run(
                    [
                        "docker",
                        "exec",
                        container,
                        "pg_isready",
                        "-h",
                        "127.0.0.1",
                        "-U",
                        "querypilot_setup",
                        "-d",
                        "querypilot_ci_test",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                ).returncode
                == 0
            ):
                print("PASS CI PostgreSQL connection readiness; migrations run in the next step")
                return
            time.sleep(1)
        raise RuntimeError("PostgreSQL readiness deadline exceeded")
    except Exception:
        subprocess.run(["docker", "rm", "-f", container], stdout=subprocess.DEVNULL, check=False)
        raise SystemExit("CI database initialization failed safely.") from None


if __name__ == "__main__":
    main()
