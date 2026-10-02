"""Exact lexical name/version/path identities and explicit snapshot schema."""

import re

from .model import InputIssue

_PART = r"[a-z0-9][a-z0-9._-]*"
_NAME = re.compile(rf"(?:@{_PART}/)?{_PART}\Z", re.ASCII)
_VERSION = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\Z",
    re.ASCII,
)
_PATH = re.compile(r"[A-Za-z0-9@._/-]+\Z", re.ASCII)


def identity(value):
    name, version, path, role = (
        value.get(k) for k in ("name", "version", "path", "role")
    )
    if type(name) is not str or len(name) > 214 or not _NAME.fullmatch(name):
        raise InputIssue("package_name_profile")
    if type(version) is not str or len(version) > 128:
        raise InputIssue("package_version_profile")
    match = _VERSION.fullmatch(version)
    if not match or (
        match[4]
        and any(
            part.isdecimal() and len(part) > 1 and part[0] == "0"
            for part in match[4].split(".")
        )
    ):
        raise InputIssue("package_version_profile")
    if role not in ("root", "dependency") or type(role) is not str:
        raise InputIssue("package_role_profile")
    if type(path) is not str or len(path) > 1024 or not _PATH.fullmatch(path):
        raise InputIssue("package_path_profile")
    if role == "root":
        if path != ".":
            raise InputIssue("root_path_profile")
    elif path.startswith("/") or any(
        part in ("", ".", "..") for part in path.split("/")
    ):
        raise InputIssue("dependency_path_profile")
    return {"name": name, "version": version, "path": path, "role": role}


def key(item):
    return tuple(item[k] for k in ("name", "version", "path", "role"))


def validate(value, limits):
    if type(value) is not dict or set(value) != {"schema", "packages", "policy"}:
        raise InputIssue("snapshot_schema_invalid")
    if value["schema"] != "lifecycle-policy-snapshot-v1":
        raise InputIssue("snapshot_schema_version")
    packages, policies = value["packages"], value["policy"]
    if type(packages) is not list or type(policies) is not list:
        raise InputIssue("snapshot_lists_required")
    if len(packages) > limits.packages or len(policies) > limits.policies:
        raise InputIssue("snapshot_count_budget")
    instances, approvals, paths, targets = [], [], set(), set()
    for index, item in enumerate(packages):
        if type(item) is not dict or set(item) != {
            "path",
            "role",
            "binding_gyp",
            "package_json",
        }:
            raise InputIssue("package_snapshot_schema")
        package = item["package_json"]
        if type(package) is not dict:
            raise InputIssue("package_json_object_required")
        target = identity(
            {**item, "name": package.get("name"), "version": package.get("version")}
        )
        if target["path"] in paths:
            raise InputIssue("package_duplicate_path")
        paths.add(target["path"])
        binding = item["binding_gyp"]
        if binding is not None and type(binding) is not bool:
            raise InputIssue("binding_gyp_boolean_or_null")
        instances.append(
            {**target, "index": index, "package_json": package, "binding_gyp": binding}
        )
    for index, item in enumerate(policies):
        if type(item) is not dict or set(item) != {
            "name",
            "version",
            "path",
            "role",
            "allow",
        }:
            raise InputIssue("policy_schema_invalid")
        target = identity(item)
        if type(item["allow"]) is not bool:
            raise InputIssue("policy_boolean_required")
        if key(target) in targets:
            raise InputIssue("policy_duplicate_target")
        targets.add(key(target))
        approvals.append({**target, "index": index, "allow": item["allow"]})
    return instances, approvals
