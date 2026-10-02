"""A JSON report only; no package manager, script runner or policy writeback."""

import argparse
import json

from . import __version__, review
from .files import read_snapshot
from .model import InputIssue, open_report


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise InputIssue("cli_arguments_invalid")


def main(argv=None):
    parser = _Parser(
        prog="lifecycle-policy-review",
        description="Offline explicit snapshot policy review; never run scripts.",
    )
    parser.add_argument("snapshot", help="one lifecycle-policy-snapshot-v1 JSON file")
    parser.add_argument("--version", action="version", version=__version__)
    try:
        args = parser.parse_args(argv)
        result = review(read_snapshot(args.snapshot))
    except InputIssue as issue:
        result = open_report(issue.code)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return {"PASS": 0, "FAIL": 1, "OPEN": 2}[result["status"]]
