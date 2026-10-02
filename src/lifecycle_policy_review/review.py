"""Complete finite lifecycle/policy matching with independent uncertainty ledger."""

import hashlib
import json

from .entrypoints import inventory
from .json_input import decode
from .model import DEFAULT_LIMITS, InputIssue, Limits, open_report, permanent_open
from .schema import key, validate


def review(raw, *, limits=None):
    selected = DEFAULT_LIMITS if limits is None else limits
    if type(selected) is not Limits:
        return open_report("limits_type_invalid")
    digest = (
        {
            "sha256": hashlib.sha256(raw).hexdigest()
            if len(raw) <= selected.file_bytes
            else None,
            "bytes": len(raw),
        }
        if type(raw) is bytes
        else None
    )
    try:
        packages, policies = validate(decode(raw, selected), selected)
    except InputIssue as issue:
        return open_report(issue.code, digest)
    report = {
        "schema": "lifecycle-policy-review-v1",
        "status": "PASS",
        "complete": True,
        "input": digest,
        "packages": [],
        "policy": [],
        "findings": [],
        "permanently_open": permanent_open(),
    }
    failed, uncertain, capped = False, False, False

    def finding(code, severity, **positions):
        nonlocal failed, uncertain, capped
        failed |= severity == "FAIL"
        uncertain |= severity == "OPEN"
        if len(report["findings"]) < selected.findings:
            report["findings"].append({"code": code, "severity": severity, **positions})
        else:
            capped = True

    mapping = {key(item): item for item in policies}
    used, uncertain_targets = set(), set()
    for instance in packages:
        record = {k: instance[k] for k in ("index", "name", "version", "path", "role")}
        record.update(
            {
                "entrypoints": [],
                "entrypoints_complete": True,
                "decision": "NOT_REQUIRED",
            }
        )
        try:
            entries, issues = inventory(instance, selected)
            record["entrypoints"] = entries
            record["entrypoints_complete"] = not issues
            for issue in issues:
                finding(issue, "OPEN", package_index=instance["index"])
        except InputIssue as issue:
            finding(issue.code, "OPEN", package_index=instance["index"])
            record["entrypoints_complete"] = False
        if not record["entrypoints_complete"]:
            uncertain_targets.add(key(instance))
        exact = mapping.get(key(instance))
        if record["entrypoints"]:
            if exact is not None:
                used.add(exact["index"])
                record["policy_index"] = exact["index"]
                record["decision"] = "APPROVED" if exact["allow"] else "DENIED"
            else:
                drift = [
                    item["index"]
                    for item in policies
                    if item["name"] == instance["name"]
                    and item["path"] == instance["path"]
                    and item["role"] == instance["role"]
                ]
                record["decision"] = "VERSION_DRIFT" if drift else "MISSING"
                finding(
                    record["decision"].lower() + "_policy",
                    "FAIL",
                    package_index=instance["index"],
                    related_policy_indices=drift,
                )
        elif not record["entrypoints_complete"]:
            record["decision"] = "UNKNOWN_ENTRYPOINTS"
        report["packages"].append(record)
    for policy in policies:
        record = dict(policy)
        if policy["index"] in used:
            record["state"] = "MATCHED"
        elif key(policy) in uncertain_targets:
            record["state"] = "UNKNOWN_ENTRYPOINTS"
        else:
            record["state"] = "STALE"
            finding("stale_policy", "FAIL", policy_index=policy["index"])
        report["policy"].append(record)
    if not packages:
        finding("empty_inventory", "OPEN")
    if capped:
        uncertain = True
        report["findings_truncated"] = True
    report["complete"] = not uncertain
    report["status"] = "FAIL" if failed else "OPEN" if uncertain else "PASS"
    encoded = json.dumps(report, ensure_ascii=True, separators=(",", ":")).encode()
    if len(encoded) > selected.report_bytes:
        compact = open_report("report_byte_budget", digest)
        compact["status"] = "FAIL" if failed else "OPEN"
        compact["known_policy_failure_observed"] = failed
        return compact
    return report
