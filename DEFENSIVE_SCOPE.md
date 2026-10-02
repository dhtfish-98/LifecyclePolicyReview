# Finite defensive contract

The selected upstream is LavaMoat/allow-scripts, fixed at
`f93c7e60a7ed5c20b0ec1993604d293cb31a079a`. The selected source closure, side-effecting
entrypoints, tests, package metadata and full MIT terms were read before this
implementation. Only explicit snapshot inventory and static policy comparison
are reimplemented. Upstream execution, setup, bin linking, auto migrations,
configuration writeback, sandbox kernels and code transforms are removed.

## Entrypoints

The finite potential-event catalog is preinstall, install, postinstall, prepublish,
preprepare, prepare, postprepare and dependencies. These are metadata candidates,
not a prediction of a particular npm command. Prepare and dependencies may depend
on installation origin or module changes; those contexts remain OPEN. Other script
names such as test/start/custom are outside this catalog. Their string metadata
is validated within bounds, but they are not interpreted or run.

Implicit install is `node-gyp rebuild` when binding_gyp is true, gypfile is not
false, and neither preinstall nor install has a nonempty string command. Empty
strings do not suppress it in the fixed @npmcli/run-script10.0.4 branch. This
deliberately follows that execution branch rather than allow-scripts' older
property-presence inventory shortcut. Whitespace is nonempty. Only absent/boolean
gypfile is supported; ambiguous types are OPEN. A null binding_gyp is an unknown
observation, producing OPEN when it can affect the implicit entrypoint. No source
file is consulted. Unknown metadata preserves known valid hooks and other known
policy failures.

References: [npm11 lifecycle documentation](https://docs.npmjs.com/cli/v11/using-npm/scripts/)
and [fixed run-script branch](https://github.com/npm/run-script/blob/08ad35e66f0d09ed7a6b85b9a457e54859b70acd/lib/run-script-pkg.js).
No claim about every npm version, operation, platform, environment or config.

## Identity and policy

Snapshot and policy wrappers have exact keys; package_json may contain other
normal JSON metadata that is ignored semantically and still checked for resource
limits. Names use the documented lowercase ASCII scoped/unscoped subset. Versions
are exact SemVer-shaped strings, including prerelease/build identifiers. Version
ranges, automatic normalization and wildcard policies are refused. Build metadata
also binds lexically. Paths have an explicit finite ASCII profile and no empty,
absolute, dot, dotdot or backslash components; `.` is root-only. They are opaque
labels, not file identities or dependency resolution. One supplied path cannot
describe two package instances. Policies bind name+version+path+role; duplicate
targets and non-boolean allow values are OPEN.

For known potential hooks, exact true/false policies yield APPROVED/DENIED.
Missing exact policy is a known FAIL. An approval for a different version of the
same name/path/role additionally reports VERSION_DRIFT. Unused approval/denial,
removed package and fully known removed hooks produce STALE/FAIL. Unknown hooks
cannot falsely make an exact policy stale. Roots receive no implicit bypass.

PASS means this finite snapshot comparison completed without missing/stale
policy. Denial is a resolved policy decision, not an observed block. Known FAIL
takes precedence over OPEN; `complete:false` preserves uncertainty separately.
Structural/schema ambiguity produces OPEN without guessed decisions. Empty
inventory is OPEN. A report budget yields compact OPEN or preserved known FAIL;
finding truncation preserves known failures and marks incompleteness.

## Bounds and observations

Default ceilings:4MiB snapshot, JSON depth48/nodes50000,512 instances,1024 policies,
64 scripts/instance,16KiB command,64KiB JSON string,4096 findings,2MiB output. Limits
must be exact positive integers at or below defaults; report minimum1024 bytes.
Strict UTF8 JSON refuses duplicate keys, nonfinite/decimal numbers, enormous
integers, unpaired surrogates and extra wrapper keys. The input profile is narrower
than every possible JSON package.json; unsupported metadata yields OPEN.

The API performs no file access, target imports, subprocess or network activity.
The CLI reads one explicit bounded regular snapshot through held directory
descriptors, with NOFOLLOW on every component and before/after descriptor metadata.
Symlinks, devices, FIFOs, noncanonical paths, changes and unsupported platforms are
refused. This observes a descriptor and is not an atomic/authenticated filesystem
snapshot. Reports show explicit identity labels; do not put secrets in them.

Source authenticity, full dependency graph, shell semantics, target script safety,
real execution/enforcement, identity/organization/model/channel and actual CVP
eligibility are always OPEN. No upstream endorsement, independent human review or
safeguard bypass is claimed.
