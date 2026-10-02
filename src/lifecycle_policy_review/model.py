"""Finite input/profile limits and sanitized errors, without target execution."""

from dataclasses import dataclass, fields


class InputIssue(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Limits:
    file_bytes: int = 4 * 1024 * 1024
    depth: int = 48
    nodes: int = 50000
    packages: int = 512
    policies: int = 1024
    scripts: int = 64
    script_bytes: int = 16384
    string_bytes: int = 65536
    findings: int = 4096
    report_bytes: int = 2 * 1024 * 1024

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            ceiling = field.default
            minimum = 1024 if field.name == "report_bytes" else 1
            if type(value) is not int or not minimum <= value <= ceiling:
                raise InputIssue("limits_invalid")


DEFAULT_LIMITS = Limits()
HOOKS = (
    "preinstall",
    "install",
    "postinstall",
    "prepublish",
    "preprepare",
    "prepare",
    "postprepare",
    "dependencies",
)


def open_report(code, identity=None):
    return {
        "schema": "lifecycle-policy-review-v1",
        "status": "OPEN",
        "complete": False,
        "input": identity,
        "packages": [],
        "policy": [],
        "findings": [{"code": code, "severity": "OPEN"}],
        "permanently_open": permanent_open(),
    }


def permanent_open():
    return {
        "inventory_authenticity": "OPEN",
        "dependency_graph_completeness": "OPEN",
        "npm_operation_schedule": "OPEN",
        "script_safety": "OPEN",
        "actual_enforcement": "OPEN",
        "cvp_eligibility": "OPEN",
    }
