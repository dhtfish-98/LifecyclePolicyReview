# LifecyclePolicyReview

Offline **allow-scripts selected static policy reimplementation**. A byte-bounded,
caller-supplied snapshot contains package.json objects, explicit instance paths,
root/dependency roles, binding.gyp observations and exact boolean policies. The
tool identifies potential lifecycle entrypoints and reports approval, denial,
missing approval, version drift and stale policies. It never runs these commands,
installs packages, walks node_modules, edits a policy or activates enforcement.

This is new AI-assisted code based on a fully reviewed, fixed allow-scripts source
subset. It is not a LavaMoat sandbox rewrite or an upstream contribution. See
[SOURCE_REVIEW.json](SOURCE_REVIEW.json) for identities and scope, and
[DEFENSIVE_SCOPE.md](DEFENSIVE_SCOPE.md) for the finite report contract.

## Use

Python3.11–3.14 on Linux/macOS. The runtime has no external dependencies.

```sh
python -m pip install --no-index --no-deps dist/lifecycle_policy_review-0.1.0-py3-none-any.whl
lifecycle-policy-review snapshot.json
```

Create `snapshot.json` yourself using this explicit schema:

```json
{
  "schema": "lifecycle-policy-snapshot-v1",
  "packages": [
    {
      "path": "node_modules/example",
      "role": "dependency",
      "binding_gyp": false,
      "package_json": {
        "name": "example",
        "version": "1.0.0",
        "scripts": {"postinstall": "node build.js"}
      }
    }
  ],
  "policy": [
    {
      "name": "example", "version": "1.0.0",
      "path": "node_modules/example", "role": "dependency", "allow": false
    }
  ]
}
```

This example yields a finite policy PASS with the instance DENIED. This decision
does not change npm behavior. `allow:true` means APPROVED under the supplied
policy; it does not establish script safety. Missing exact approval is FAIL.
Upgrading to1.1.0 leaves the old approval stale and produces VERSION_DRIFT.

Library use receives immutable bytes, never a dependency directory:

```python
from lifecycle_policy_review import Limits, review
report = review(snapshot_bytes, limits=Limits(packages=128))
```

Both root and dependency instances use explicit policies. A root has path `.`;
dependency paths are canonical relative POSIX labels, compared literally and
never dereferenced. Two instances of the same package at different paths require
two approvals. These labels, package names and versions appear in reports. Local
CLI snapshot filenames and script bodies do not; command bytes are represented
by length, SHA256 and JSON source pointer. Metadata and hashes are untrusted.

Exit0 is finite PASS, exit1 is a known policy FAIL, exit2 is OPEN. CLI errors use
fixed JSON codes without paths, supplied arguments or exception text. `--help`
and `--version` return fixed text. All source/authenticity, dependency completeness,
actual npm scheduling, safety, enforcement and CVP applicability remain OPEN.

## Development

```sh
python -m pip install -r requirements-dev.txt
PYTHONPATH=src python -m unittest discover -s tests -v
ruff check src tests scripts
ruff format --check src tests scripts
python -m build --no-isolation
```

CI tests source and a freshly installed wheel from another directory on Linux
and macOS with Python3.11 and3.14. [VALIDATION.md](VALIDATION.md) separates observed
checks from publication and unsupported claims. Source and notices use MIT terms;
the complete upstream Consensys license is preserved in `licenses/`.
