import copy
import hashlib
import json
import random
import unittest

from fixtures import encoded, instance, policy, snapshot

from lifecycle_policy_review import Limits, review
from lifecycle_policy_review.model import HOOKS, InputIssue


class ReviewTests(unittest.TestCase):
    def test_no_entrypoint(self):
        result = review(encoded(snapshot()))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["packages"][0]["decision"], "NOT_REQUIRED")

    def test_explicit_approval_and_denial(self):
        package = instance(scripts={"install": "DO_NOT_EXECUTE_PRIVATE_BODY"})
        for allow, expected in ((True, "APPROVED"), (False, "DENIED")):
            result = review(encoded(snapshot([package], [policy(package, allow)])))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["packages"][0]["decision"], expected)
            self.assertEqual(result["policy"][0]["state"], "MATCHED")
            self.assertNotIn("DO_NOT_EXECUTE_PRIVATE_BODY", json.dumps(result))
            self.assertEqual(result["permanently_open"]["script_safety"], "OPEN")

    def test_missing_policy(self):
        result = review(encoded(snapshot([instance(scripts={"prepare": "build"})])))
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["findings"][0]["code"], "missing_policy")

    def test_version_drift(self):
        old = instance(version="1.0.0", scripts={"postinstall": "prepare"})
        new = instance(version="1.1.0", scripts={"postinstall": "prepare"})
        result = review(encoded(snapshot([new], [policy(old)])))
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(
            [x["code"] for x in result["findings"]],
            ["version_drift_policy", "stale_policy"],
        )

    def test_two_instances_need_two_approvals(self):
        one = instance(scripts={"preinstall": "build"})
        two = instance(
            path="node_modules/outer/node_modules/sample",
            scripts={"preinstall": "build"},
        )
        result = review(encoded(snapshot([one, two], [policy(one)])))
        self.assertEqual(
            [x["decision"] for x in result["packages"]], ["APPROVED", "MISSING"]
        )
        self.assertEqual(
            review(encoded(snapshot([one, two], [policy(one), policy(two)])))["status"],
            "PASS",
        )

    def test_root_does_not_bypass_policy(self):
        root = instance(path=".", role="root", scripts={"prepare": "build"})
        self.assertEqual(review(encoded(snapshot([root])))["status"], "FAIL")
        self.assertEqual(
            review(encoded(snapshot([root], [policy(root, False)])))["packages"][0][
                "decision"
            ],
            "DENIED",
        )

    def test_stale_removed_package(self):
        result = review(
            encoded(snapshot([instance()], [policy(instance(name="removed"))]))
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["policy"][0]["state"], "STALE")

    def test_stale_removed_script_even_denied(self):
        package = instance()
        for allow in (True, False):
            self.assertEqual(
                review(encoded(snapshot([package], [policy(package, allow)])))[
                    "status"
                ],
                "FAIL",
            )

    def test_all_finite_hooks_and_ignored_test(self):
        scripts = {key: "private" for key in HOOKS}
        scripts["test"] = "PRIVATE_TEST_BODY"
        package = instance(scripts=scripts)
        result = review(encoded(snapshot([package], [policy(package)])))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            [x["event"] for x in result["packages"][0]["entrypoints"]], list(HOOKS)
        )

    def test_implicit_gyp(self):
        package = instance(binding=True)
        result = review(encoded(snapshot([package], [policy(package)])))
        self.assertEqual(result["status"], "PASS")
        entry = result["packages"][0]["entrypoints"][0]
        self.assertEqual(entry["event"], "install")
        self.assertEqual(entry["kind"], "implicit_node_gyp")

    def test_empty_string_gyp_truthiness(self):
        package = instance(binding=True, scripts={"install": "", "preinstall": ""})
        result = review(encoded(snapshot([package], [policy(package)])))
        self.assertEqual(
            result["packages"][0]["entrypoints"][0]["kind"], "implicit_node_gyp"
        )

    def test_nonempty_preinstall_suppresses_gyp(self):
        package = instance(binding=True, scripts={"preinstall": " "})
        result = review(encoded(snapshot([package], [policy(package)])))
        self.assertEqual(
            [x["event"] for x in result["packages"][0]["entrypoints"]], ["preinstall"]
        )

    def test_gypfile_false_and_missing_binding(self):
        package = instance(binding=None)
        package["package_json"]["gypfile"] = False
        self.assertEqual(review(encoded(snapshot([package])))["status"], "PASS")
        package["package_json"].pop("gypfile")
        self.assertEqual(review(encoded(snapshot([package])))["status"], "OPEN")

    def test_unknown_binding_preserves_missing_policy(self):
        package = instance(binding=None, scripts={"prepare": "build"})
        result = review(encoded(snapshot([package])))
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["complete"])

    def test_unknown_binding_cannot_make_false_stale(self):
        package = instance(binding=None)
        result = review(encoded(snapshot([package], [policy(package)])))
        self.assertEqual(result["status"], "OPEN")
        self.assertEqual(result["policy"][0]["state"], "UNKNOWN_ENTRYPOINTS")

    def test_script_type_invalid_preserves_other_failure(self):
        invalid = instance(name="other", path="node_modules/other")
        invalid["package_json"]["scripts"] = None
        result = review(
            encoded(snapshot([instance(scripts={"install": "x"}), invalid]))
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["complete"])

    def test_unsupported_script_and_gyp_types(self):
        for value in (None, False, 0, [], "wrong"):
            package = instance()
            package["package_json"]["scripts"] = value
            self.assertEqual(review(encoded(snapshot([package])))["status"], "OPEN")
        for value in (0, "false", None):
            package = instance()
            package["package_json"]["gypfile"] = value
            self.assertEqual(review(encoded(snapshot([package])))["status"], "OPEN")

    def test_policy_bool_is_exact(self):
        package = instance(scripts={"install": "x"})
        for value in (1, 0, "true", None, []):
            item = policy(package)
            item["allow"] = value
            self.assertEqual(
                review(encoded(snapshot([package], [item])))["status"], "OPEN"
            )

    def test_duplicate_policy_and_path(self):
        package = instance(scripts={"install": "x"})
        self.assertEqual(
            review(
                encoded(snapshot([package], [policy(package), policy(package, False)]))
            )["status"],
            "OPEN",
        )
        self.assertEqual(
            review(encoded(snapshot([package, package])))["status"], "OPEN"
        )

    def test_versions_are_exact_not_ranges(self):
        for version in (
            "^1.0.0",
            "v1.0.0",
            "01.0.0",
            "1.0.0-01",
            "1.0",
            "1.0.0\n",
            "１.0.0",
        ):
            self.assertEqual(
                review(encoded(snapshot([instance(version=version)])))["status"], "OPEN"
            )
        for version in ("0.0.0", "1.2.3-beta.1+build", "1.2.3+001"):
            self.assertEqual(
                review(encoded(snapshot([instance(version=version)])))["status"], "PASS"
            )

    def test_exact_build_version_not_automatic_upgrade(self):
        old = instance(version="1.2.3+old", scripts={"install": "x"})
        new = instance(version="1.2.3+new", scripts={"install": "x"})
        self.assertEqual(
            review(encoded(snapshot([new], [policy(old)])))["packages"][0]["decision"],
            "VERSION_DRIFT",
        )

    def test_name_profile_scoped_and_no_coercion(self):
        self.assertEqual(
            review(encoded(snapshot([instance(name="@scope/pkg")])))["status"], "PASS"
        )
        for name in ("Upper", "pkg/other", "@scope", "_prefix", "private\n", 3):
            self.assertEqual(
                review(encoded(snapshot([instance(name=name)])))["status"], "OPEN"
            )

    def test_path_canonical_and_role(self):
        for path in ("/absolute", "../escape", "a//b", "a/./b", "a/../b", "a\\b", "."):
            self.assertEqual(
                review(encoded(snapshot([instance(path=path)])))["status"], "OPEN"
            )
        self.assertEqual(
            review(encoded(snapshot([instance(path="different", role="root")])))[
                "status"
            ],
            "OPEN",
        )

    def test_strict_json_and_duplicate_nested(self):
        cases = [
            b"{}",
            b"\xef\xbb\xbf{}",
            b'{"x":NaN}',
            b'{"x":1.0}',
            b'{"x":Infinity}',
            b'{"x":"\\ud800"}',
            b'{"x":1,"x":2}',
            b'{"a":{"b":1,"b":2}}',
            b"\xff",
            b"{} trailing",
        ]
        for raw in cases:
            self.assertEqual(review(raw)["status"], "OPEN")

    def test_bytes_only_and_false_limits(self):
        for value in (None, "{}", bytearray(b"{}"), memoryview(b"{}")):
            self.assertEqual(review(value)["status"], "OPEN")
        for value in (False, 0, {}, "default"):
            self.assertEqual(
                review(encoded(snapshot()), limits=value)["status"], "OPEN"
            )

    def test_lower_limits_and_constructor_exactness(self):
        for value in (0, True, -1, 49):
            with self.assertRaises(InputIssue):
                Limits(depth=value)
        package = instance(scripts={"install": "123"})
        self.assertEqual(
            review(encoded(snapshot([package])), limits=Limits(script_bytes=2))[
                "status"
            ],
            "OPEN",
        )
        self.assertEqual(
            review(encoded(snapshot()), limits=Limits(file_bytes=4))["status"], "OPEN"
        )

    def test_json_nesting_and_strings_not_braces(self):
        value = snapshot()
        value["packages"][0]["package_json"]["notes"] = '[{\\"' * 30
        self.assertEqual(
            review(encoded(value), limits=Limits(depth=8))["status"], "PASS"
        )
        value["packages"][0]["package_json"]["notes"] = [[[[[[[[]]]]]]]]
        self.assertEqual(
            review(encoded(value), limits=Limits(depth=8))["status"], "OPEN"
        )

    def test_finding_budget_keeps_failure(self):
        packages = [
            instance(name=f"p{i}", path=f"node_modules/p{i}", scripts={"install": "x"})
            for i in range(3)
        ]
        result = review(encoded(snapshot(packages)), limits=Limits(findings=1))
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["complete"])
        self.assertTrue(result["findings_truncated"])

    def test_report_budget_keeps_failure(self):
        packages = [
            instance(name=f"p{i}", path=f"node_modules/p{i}", scripts={"install": "x"})
            for i in range(3)
        ]
        result = review(encoded(snapshot(packages)), limits=Limits(report_bytes=1024))
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["complete"])
        self.assertTrue(result["known_policy_failure_observed"])

    def test_known_entrypoint_failure_survives_unknown_same_package(self):
        package = instance(scripts={"prepare": "build", "test": 0})
        package["package_json"]["gypfile"] = None
        result = review(encoded(snapshot([package])))
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["complete"])
        self.assertEqual(result["packages"][0]["decision"], "MISSING")

    def test_empty_inventory_open(self):
        self.assertEqual(review(encoded(snapshot([])))["status"], "OPEN")

    def test_input_unchanged_deterministic(self):
        value = snapshot([instance(scripts={"install": "PRIVATE_BODY"})])
        original = copy.deepcopy(value)
        raw = encoded(value)
        result = review(raw)
        self.assertEqual(value, original)
        self.assertEqual(result, review(raw))
        self.assertEqual(result["input"]["sha256"], hashlib.sha256(raw).hexdigest())

    def test_seeded_malformed_no_crash(self):
        randomizer = random.Random(173)
        for _ in range(1000):
            raw = randomizer.randbytes(randomizer.randrange(1, 256))
            result = review(raw)
            self.assertIn(result["status"], ("PASS", "FAIL", "OPEN"))
            json.dumps(result)


if __name__ == "__main__":
    unittest.main()
