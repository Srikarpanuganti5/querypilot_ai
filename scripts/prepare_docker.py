"""Generate private URL-safe Compose credentials without changing native .env settings."""

import os
import secrets
from pathlib import Path


def prepare(path: Path = Path(".env.docker")) -> bool:
    if path.exists() or path.is_symlink():
        print("SKIP existing Docker configuration preserved")
        return False
    with path.open("x", encoding="utf-8") as output:
        os.chmod(path, 0o600)
        output.write(
            f"QP_SETUP_PASSWORD={secrets.token_hex(24)}\n"
            f"QP_READER_PASSWORD={secrets.token_hex(24)}\n"
            "QP_BACKEND_PORT=18000\nQP_FRONTEND_PORT=18501\n"
        )
    print("PASS private .env.docker created; credentials are not printed")
    return True


if __name__ == "__main__":
    prepare()
