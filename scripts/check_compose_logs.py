"""Check bounded Compose logs in memory without echoing secret-bearing content."""

import subprocess

from dotenv import dotenv_values

from querypilot.core.security import SecretGuard


def main() -> None:
    values = dotenv_values(".env.docker")
    logs = subprocess.check_output(
        ["docker", "compose", "--env-file", ".env.docker", "logs", "--no-color", "--tail", "1000"],
        stderr=subprocess.STDOUT,
        text=True,
    )
    secrets = [values.get(key) for key in ["QP_SETUP_PASSWORD", "QP_READER_PASSWORD"]]
    if any(value and value in logs for value in secrets) or SecretGuard().contains(logs):
        raise SystemExit("FAIL: credential-like content detected; raw logs withheld.")
    print(
        "PASS bounded Compose log scan; no configured credentials or credential patterns detected"
    )


if __name__ == "__main__":
    main()
