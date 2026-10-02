"""Launch this installed CLI with synthetic snapshots, never target commands."""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    import lifecycle_policy_review

    root = Path(__file__).resolve().parents[1]
    assert root / "src" not in Path(lifecycle_policy_review.__file__).parents
    binary = Path(sys.executable).parent / "lifecycle-policy-review"
    package = {
        "path": "node_modules/sample",
        "role": "dependency",
        "binding_gyp": False,
        "package_json": {
            "name": "sample",
            "version": "1.0.0",
            "scripts": {"install": "PRIVATE_BODY_NEVER_RUN"},
        },
    }
    approve = {
        "name": "sample",
        "version": "1.0.0",
        "path": "node_modules/sample",
        "role": "dependency",
        "allow": False,
    }
    with tempfile.TemporaryDirectory() as name:
        folder = Path(name).resolve()
        value = {
            "schema": "lifecycle-policy-snapshot-v1",
            "packages": [package],
            "policy": [approve],
        }
        target = folder / "PRIVATE_SNAPSHOT_NAME.json"
        target.write_text(json.dumps(value))
        missing = folder / "missing.json"
        no_policy = folder / "missing-policy.json"
        no_policy.write_text(json.dumps({**value, "policy": []}))
        invalid = folder / "invalid.json"
        invalid.write_bytes(b"not JSON")
        link = folder / "link.json"
        link.symlink_to(target)
        before = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (target, no_policy, invalid)
        }
        cases = [
            ([str(target)], 0),
            ([str(no_policy)], 1),
            ([str(invalid)], 2),
            ([str(missing)], 2),
            ([str(link)], 2),
            (["--UNKNOWN_PRIVATE_ARGUMENT"], 2),
        ]
        for arguments, status in cases:
            child = subprocess.run(
                [str(binary), *arguments],
                cwd=folder,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            assert child.returncode == status and not child.stderr
            result = json.loads(child.stdout)
            assert result["status"] == {0: "PASS", 1: "FAIL", 2: "OPEN"}[status]
            assert "PRIVATE_BODY_NEVER_RUN" not in child.stdout
            assert (
                "PRIVATE_SNAPSHOT_NAME" not in child.stdout
                and str(folder) not in child.stdout
            )
            assert "UNKNOWN_PRIVATE_ARGUMENT" not in child.stdout
        for option in ("--help", "--version"):
            child = subprocess.run(
                [str(binary), option],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            assert child.returncode == 0 and not child.stderr
        after = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (target, no_policy, invalid)
        }
        assert before == after
    print(
        json.dumps(
            {
                "status": "PASS",
                "CLI_JSON_cases": 6,
                "static_help_version_cases": 2,
                "input_unchanged": True,
                "installed_module": str(lifecycle_policy_review.__file__),
            }
        )
    )


if __name__ == "__main__":
    main()
