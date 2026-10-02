"""Potential metadata hooks, not an npm operation scheduler or shell analyzer."""

import hashlib

from .model import HOOKS


def inventory(instance, limits):
    package = instance["package_json"]
    scripts = package.get("scripts", {})
    if type(scripts) is not dict:
        return [], ["scripts_object_required"]
    issues = []
    if len(scripts) > limits.scripts:
        issues.append("scripts_count_budget")
    for index, script in enumerate(scripts.values()):
        if index >= limits.scripts:
            break
        if type(script) is not str:
            issues.append("script_string_required")
        elif len(script.encode("utf-8")) > limits.script_bytes:
            issues.append("script_byte_budget")
    entries = []
    for hook in HOOKS:
        command = scripts.get(hook, "")
        if type(command) is not str:
            issues.append("selected_script_string_required")
        elif len(command.encode("utf-8")) > limits.script_bytes:
            issues.append("selected_script_byte_budget")
        elif command:
            raw = command.encode("utf-8")
            entries.append(
                {
                    "event": hook,
                    "kind": "declared",
                    "command_bytes": len(raw),
                    "command_sha256": hashlib.sha256(raw).hexdigest(),
                    "source_pointer": f"/packages/{instance['index']}/package_json/scripts/{hook}",
                }
            )
    gypfile = package.get("gypfile", True)
    if type(gypfile) is not bool:
        return entries, list(dict.fromkeys([*issues, "gypfile_boolean_profile"]))
    # @npmcli/run-script10.0.4 checks truthiness, not property presence.
    # Empty strings don't suppress the implicit install. No files are inspected.
    suppressors = [scripts.get("preinstall", ""), scripts.get("install", "")]
    if gypfile and any(type(value) is not str for value in suppressors):
        issues.append("implicit_gyp_suppressor_unknown")
    elif gypfile and not any(suppressors):
        binding = instance["binding_gyp"]
        if binding is None:
            issues.append("binding_gyp_observation_missing")
        elif binding:
            command = b"node-gyp rebuild"
            entries.append(
                {
                    "event": "install",
                    "kind": "implicit_node_gyp",
                    "command_bytes": len(command),
                    "command_sha256": hashlib.sha256(command).hexdigest(),
                    "source_pointer": f"/packages/{instance['index']}/binding_gyp",
                }
            )
    return entries, list(dict.fromkeys(issues))
