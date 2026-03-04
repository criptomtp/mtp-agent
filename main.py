#!/usr/bin/env python3
"""MTP Fulfillment — Lead Generation Agent. Точка входу."""

import sys
from agents.orchestrator import Orchestrator


def main():
    count = 5
    send_email = False

    args = sys.argv[1:]

    for arg in args:
        if arg == "--send":
            send_email = True
        elif arg.isdigit():
            count = int(arg)

    orchestrator = Orchestrator(send_email=send_email)
    result_dir = orchestrator.run(count)

    print(f"Результати збережено в: {result_dir}")


if __name__ == "__main__":
    main()
