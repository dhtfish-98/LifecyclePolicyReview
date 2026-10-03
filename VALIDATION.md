# Current delivery validation — 0.1.1

New implementation author and maintainer: dhtfish98. Current source inventory: `SOURCE_REVIEW_MANIFEST.json` (this manifest excludes its own digest). The 2026-10-03 delivery preserves original upstream license and notice bytes; current runtime additionally validates the required OS capability flags and directory-relative support before local file reads.

The existing suite has 42 passing test cases in the current source and in a fresh consumer of this version. Package verification checks version/author, artifact RECORD or archive inventories, runtime bytes against the formal source, and retained third-party licenses. Consumer installation uses local frozen dependencies and does not run target inputs. Detailed current artifact hashes and execution receipts are kept in the separate delivery evidence.

New-commit hosted CI and publication remain pending until the repository owner publishes this version.

These engineering checks do not establish upstream authorship, independent human review, actual safeguards impact or CVP eligibility.

## Historical delivery evidence

The following sections describe the earlier delivery and retain its original versions and checks. They do not validate a later artifact.

# Validation ledger

The selected41 fixed upstream files (9 runtime JS files, type contract, package,
README, complete licenses,4 test helpers/specs and23 fixture package.json files)
were fully read and their Git blob/byte identities verified. npm's selected
run-script10.0.4 command-selection branch was separately read; other execution
machinery is excluded. See SOURCE_REVIEW.json for exact identities and coverage.

The local source suite currently has38 methods, including1000 deterministic
malformed byte cases, all finite hooks, root/dependency exact policy, two instances,
version/build drift, stale approvals, implicit gyp/empty string/unknown metadata,
nonboolean coercion, strict JSON, budget failure precedence, deterministic hashes,
regular input identity, leaf/ancestor symlink/FIFO refusal, and library audit
observations. Tests never run a supplied script or upstream command.

Actual fresh wheel install, the same suite outside the source tree,8 installed
CLI controls, archive/RECORD/installed source/license comparison and independent
agent semantic review are tracked separately in evidence. A test description or
build artifact does not claim that any unrun check passed. The CI configuration
defines4 OS/Python combinations; exact commit remote success requires live proof.

Publication and release proofs live in the parent engineering ledger and are
checked after review. No human review, actual npm enforcement, script safety,
authenticated package snapshot, whole dependency graph or CVP approval is proven.
