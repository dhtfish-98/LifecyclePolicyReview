"""Check our trusted built artifacts by bytes without extracting archive input."""

import argparse
import base64
import csv
import hashlib
import io
import json
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath


def verify(project, installed):
    metadata = tomllib.loads((project / "pyproject.toml").read_text())["project"]
    whls = list((project / "dist").glob("*.whl"))
    tars = list((project / "dist").glob("*.tar.gz"))
    assert len(whls) == len(tars) == 1
    modules = {
        p.relative_to(project / "src").as_posix(): p.read_bytes()
        for p in (project / "src").rglob("*")
        if p.is_file() and (p.suffix == ".py" or p.name == "py.typed")
    }
    licenses = sorted(
        {
            p.relative_to(project).as_posix()
            for pattern in metadata["license-files"]
            for p in project.glob(pattern)
            if p.is_file()
        }
    )
    with zipfile.ZipFile(whls[0]) as archive:
        names = archive.namelist()
        assert len(set(names)) == len(names)
        assert all(
            not name.startswith("/") and ".." not in PurePosixPath(name).parts
            for name in names
        )
        records = [name for name in names if name.endswith(".dist-info/RECORD")]
        assert len(records) == 1
        rows = list(csv.reader(io.StringIO(archive.read(records[0]).decode("utf-8"))))
        assert {row[0] for row in rows} == set(names) and len(rows) == len(names)
        for name, expected, length in rows:
            raw = archive.read(name)
            if name == records[0]:
                assert expected == length == ""
            else:
                actual = (
                    base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
                    .decode()
                    .rstrip("=")
                )
                assert expected == "sha256=" + actual and int(length) == len(raw)
        for name, raw in modules.items():
            assert archive.read(name) == raw
            assert (installed / name).read_bytes() == raw
        description = BytesParser().parsebytes(
            archive.read(
                next(name for name in names if name.endswith(".dist-info/METADATA"))
            )
        )
        assert (
            description["Name"] == metadata["name"]
            and description["Version"] == metadata["version"]
        )
        assert description["License-Expression"] == metadata["license"]
        assert description.get_all("Requires-Dist", []) == []
        assert sorted(description.get_all("License-File", [])) == licenses
        for name in licenses:
            match = next(
                item for item in names if item.endswith(".dist-info/licenses/" + name)
            )
            assert archive.read(match) == (project / name).read_bytes()
    matched, seen, prefixes = 0, set(), set()
    with tarfile.open(tars[0], "r:gz") as archive:
        for member in archive:
            parts = PurePosixPath(member.name).parts
            assert parts and not member.name.startswith("/") and ".." not in parts
            assert member.name not in seen and (member.isfile() or member.isdir())
            assert not any(
                part in (".git", ".venv", "validation-local", "__pycache__")
                for part in parts
            )
            seen.add(member.name)
            prefixes.add(parts[0])
            relative = Path(*parts[1:])
            local = project / relative
            if member.isfile() and local.is_file():
                assert archive.extractfile(member).read() == local.read_bytes()
                matched += 1
        assert len(prefixes) == 1
        for name in list(modules) + licenses:
            expected = "src/" + name if name in modules else name
            assert any(member.endswith("/" + expected) for member in seen)
    return {
        "status": "PASS",
        "wheel_RECORD_rows": len(rows),
        "runtime_files": len(modules),
        "sdist_local_files": matched,
        "license_files": licenses,
        "artifacts": [
            {
                "name": p.name,
                "bytes": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            }
            for p in whls + tars
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--installed", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = verify(args.project, args.installed)
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
