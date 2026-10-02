import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from fixtures import encoded, instance, policy, snapshot

from lifecycle_policy_review import review
from lifecycle_policy_review.files import read_snapshot
from lifecycle_policy_review.model import InputIssue


class InputTests(unittest.TestCase):
    def test_regular_snapshot_input_unchanged(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name).resolve()
            target = folder / "snapshot.json"
            raw = encoded(snapshot())
            target.write_bytes(raw)
            before = hashlib.sha256(target.read_bytes()).hexdigest()
            self.assertEqual(read_snapshot(str(target)), raw)
            self.assertEqual(before, hashlib.sha256(target.read_bytes()).hexdigest())

    def test_symlink_leaf_and_ancestor_refused(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name).resolve()
            real = folder / "real"
            real.mkdir()
            target = real / "snapshot.json"
            target.write_bytes(encoded(snapshot()))
            (folder / "leaf").symlink_to(target)
            (folder / "ancestor").symlink_to(real, target_is_directory=True)
            for path in (folder / "leaf", folder / "ancestor" / "snapshot.json"):
                with self.assertRaises(InputIssue):
                    read_snapshot(str(path))

    def test_special_and_directory_refused_without_blocking(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name).resolve()
            fifo = folder / "fifo"
            os.mkfifo(fifo)
            for path in (fifo, folder):
                with self.assertRaises(InputIssue):
                    read_snapshot(str(path))

    def test_components_and_invalid_path(self):
        for value in ("", "a//b", "a/../b", "a/./b", "a/", "a\0", "\ud800", None):
            with self.assertRaises(InputIssue):
                read_snapshot(value)

    def test_library_observation_no_target_activity(self):
        package = instance(scripts={"install": "PRIVATE_NEVER_EXECUTE"}, binding=True)
        cases = [
            encoded(snapshot()),
            encoded(snapshot([package])),
            encoded(snapshot([package], [policy(package)])),
            b"not json",
        ]
        # Imports needed by the harness have happened before activation. The
        # installed library itself imports its fixed stdlib closure eagerly.
        json.dumps(review(cases[0]))
        observed = []
        active = [True]

        def audit(event, args):
            if active[0] and (
                event in ("exec", "import", "open")
                or event.startswith(("socket.", "subprocess.", "os.system", "os.spawn"))
            ):
                observed.append(event)

        sys.addaudithook(audit)
        try:
            for raw in cases:
                json.dumps(review(raw))
        finally:
            active[0] = False
        self.assertEqual(observed, [])


if __name__ == "__main__":
    unittest.main()
