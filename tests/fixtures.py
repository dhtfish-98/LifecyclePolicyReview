"""Synthetic explicit snapshots; no package targets or script execution."""

import json


def instance(
    name="sample",
    version="1.0.0",
    path="node_modules/sample",
    role="dependency",
    scripts=None,
    binding=False,
):
    return {
        "path": path,
        "role": role,
        "binding_gyp": binding,
        "package_json": {
            "name": name,
            "version": version,
            "scripts": {} if scripts is None else scripts,
        },
    }


def policy(package, allow=True):
    return {
        "name": package["package_json"]["name"],
        "version": package["package_json"]["version"],
        "path": package["path"],
        "role": package["role"],
        "allow": allow,
    }


def snapshot(packages=None, policies=None):
    return {
        "schema": "lifecycle-policy-snapshot-v1",
        "packages": [instance()] if packages is None else packages,
        "policy": [] if policies is None else policies,
    }


def encoded(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode()
