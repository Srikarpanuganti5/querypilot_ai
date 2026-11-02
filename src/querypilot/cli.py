"""Public agent CLI; existing querypilot.tools commands remain available."""

import argparse
import sys

from querypilot.agent.cli import main as ask_main


def main() -> None:
    if sys.argv[1:2] == ["ask"]:
        ask_main(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["ask"])
    parser.parse_args()


if __name__ == "__main__":
    main()
